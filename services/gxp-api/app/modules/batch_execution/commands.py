"""Document 11 (SPEC-EBMR-002) — the buildable slice of the Batch Execution Engine: create, issue (with
Vault execution snapshot + step instantiation), start, hold/resume, abort, step claim/start, step
results/complete (SG-047 partial resolution), step-scoped hold/resume, and production-complete (both
2026-09-09, project-owner-directed, SG-047/SG-048 further partial resolution). `app/modules/batch` (the
legacy Batch-facing stub) is untouched -- this module is net-new and additive (see migration
f264272f2f0b's docstring). Still deferred: gxp_step_evidence_link (SG-047), and everything else needing
infrastructure this codebase does not have yet (Temporal, Material Service consumption/reservation,
Equipment eligibility wiring -- both blocked on SG-045's still-open recipe_material_requirement/
recipe_equipment_requirement schema decision, IAM qualification schema, exception/rework/branch entities)
-- SG-048.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.batch_execution import service as batch_execution_service
from app.modules.batch_execution.models import (
    ALLOWED_TRANSITIONS,
    Batch,
    BatchStep,
    BatchStepEquipmentRequirement,
    StepComment,
    StepEvidenceLink,
    StepHandover,
    StepHold,
    StepResult,
    StepResultCorrection,
)
from app.modules.equipment import commands as equipment_commands
from app.modules.equipment.models import EquipmentAsset, EquipmentUseLog
from app.modules.genealogy import service as genealogy_service
from app.modules.iam.models import Qualification, User
from app.modules.qms import commands as qms_commands
from app.modules.policy.service import effective_role_names, evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.modules.recipe_master import service as recipe_master_service
from app.modules.recipe_master.models import RecipeEquipmentRequirement, RecipeEvidenceRequirement, RecipeParameter
from app.modules.rules import service as rules_service
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    CalibrationExpiredError,
    CalibrationOotImpactRequiredError,
    CleaningRequiredError,
    EquipmentClassMismatchError,
    EquipmentNotQualifiedError,
    EquipmentOutOfServiceError,
    EquipmentRequirementNotMetError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    ParameterRequiredError,
    PostMaintenanceVerificationRequiredError,
    ProductionNotCompleteError,
    QualificationExpiredError,
    QualificationMissingError,
    RoleMissingError,
    StaleVersionError,
    StepRoleMismatchError,
    UomUnknownError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


async def _resolve_uom_id(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    """SG-146 (remainder, module 4 of 8), MIG-FR-004 expand step."""
    if not uom:
        return None
    try:
        row = await rules_service.resolve_uom(session, uom)
    except UomUnknownError:
        return None
    return row.uom_id


async def _resolve_uom_id_strict(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    """Client requirements #2/#3: the batch-creation UI's UomSelect only ever submits a code drawn from
    the released UOM list, so an unresolvable non-empty code here means a caller sent something outside
    it -- reject instead of silently leaving target_uom_id NULL."""
    if not uom:
        return None
    uom_id = await _resolve_uom_id(session, uom)
    if uom_id is None:
        raise ValidationFailedError("Unrecognized or unreleased UOM code", uom=uom)
    return uom_id


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


async def _load_batch_for_update(session: AsyncSession, batch_id: uuid.UUID, expected_version: int) -> Batch:
    result = await session.execute(select(Batch).where(Batch.id == batch_id).with_for_update())
    batch = result.scalar_one_or_none()
    if batch is None:
        raise NotFoundError("Batch not found")
    if batch.version != expected_version:
        raise StaleVersionError(
            "Batch was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=batch.version,
        )
    return batch


async def _load_step_for_update(session: AsyncSession, batch_id: uuid.UUID, step_id: uuid.UUID, expected_version: int) -> BatchStep:
    result = await session.execute(select(BatchStep).where(BatchStep.id == step_id).with_for_update())
    step = result.scalar_one_or_none()
    if step is None or step.batch_id != batch_id:
        raise NotFoundError("Batch step not found")
    if step.version != expected_version:
        raise StaleVersionError(
            "Batch step was modified by another actor since it was read",
            expected_version=expected_version,
            current_version=step.version,
        )
    return step


def _assert_transition(batch: Batch, new_state: str) -> None:
    if new_state not in ALLOWED_TRANSITIONS.get(batch.state, set()):
        raise InvalidTransitionError("Illegal batch lifecycle transition", current_state=batch.state, requested=new_state)


# ---------------------------------------------------------------------------
# CreateBatch — BAT-FR-001/002
# ---------------------------------------------------------------------------


class CreateBatchCommand(CommandEnvelope):
    site_id: uuid.UUID
    batch_number: str
    product_version_id: uuid.UUID
    recipe_version_id: uuid.UUID
    target_qty: Decimal
    target_uom: str
    production_order_ref: str | None = None


async def create_batch(session: AsyncSession, cmd: CreateBatchCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    product_version = await session.get(ProductVersion, cmd.product_version_id)
    if product_version is None:
        raise NotFoundError("Product version not found")
    if product_version.lifecycle_state != "released":
        raise ValidationFailedError(
            "Batch can only be created against a released product version", current_state=product_version.lifecycle_state
        )

    recipe_version = await recipe_master_service.get_version(session, cmd.recipe_version_id)
    if recipe_version.lifecycle_state != "released":
        raise ValidationFailedError(
            "Batch can only be created against a released recipe version", current_state=recipe_version.lifecycle_state
        )
    if recipe_version.product_version_id != cmd.product_version_id:
        raise ValidationFailedError(
            "recipe_version_id was not authored against product_version_id",
            recipe_product_version_id=str(recipe_version.product_version_id),
        )

    conflict = (
        await session.execute(select(Batch).where(Batch.site_id == cmd.site_id, Batch.batch_number == cmd.batch_number))
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("batch_number is already in use at this site", site_id=str(cmd.site_id), batch_number=cmd.batch_number)

    batch = Batch(
        site_id=cmd.site_id,
        batch_number=cmd.batch_number,
        product_version_id=cmd.product_version_id,
        recipe_version_id=cmd.recipe_version_id,
        recipe_vault_object_id=recipe_version.released_vault_object_id,
        target_qty=cmd.target_qty,
        target_uom=cmd.target_uom,
        target_uom_id=await _resolve_uom_id_strict(session, cmd.target_uom),
        production_order_ref=cmd.production_order_ref,
        state="planned",
    )
    session.add(batch)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"batch_number": batch.batch_number, "product_version_id": str(cmd.product_version_id), "recipe_version_id": str(cmd.recipe_version_id)},
    )
    await write_outbox_event(
        session,
        event_type="BatchCreated",
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=1,
        payload={"id": str(batch.id), "batch_number": batch.batch_number},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="CreateBatch",
        aggregate_type="batch",
        aggregate_id=batch.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=batch.id, resulting_version=1, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


# ---------------------------------------------------------------------------
# IssueBatch — BAT-FR-003/004/005/006
# ---------------------------------------------------------------------------


class IssueBatchCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int


async def issue_batch(session: AsyncSession, cmd: IssueBatchCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    _assert_transition(batch, "issued")

    graph = await recipe_master_service.get_graph(session, batch.recipe_version_id)
    steps = graph["steps"]
    dependencies = graph["dependencies"]
    if not steps:
        raise ValidationFailedError("Recipe version has no steps to instantiate")

    code_by_step_id = {s.id: s.stable_step_code for s in steps}
    initial_states = batch_execution_service.compute_initial_step_states(
        [s.stable_step_code for s in steps], dependencies, code_by_step_id
    )

    # Known-limitations fix (docs/testing/demo-gujarati/08 §8.8): freeze RecipeEquipmentRequirement rows
    # the same way required_role_code/required_qualification_code are already frozen below -- a step can
    # declare more than one, grouped by the RecipeStep id they belong to.
    equipment_requirements_by_step_id: dict[uuid.UUID, list[RecipeEquipmentRequirement]] = {}
    step_ids = [s.id for s in steps]
    if step_ids:
        eq_rows = (
            await session.execute(
                select(RecipeEquipmentRequirement).where(RecipeEquipmentRequirement.step_id.in_(step_ids))
            )
        ).scalars().all()
        for eq in eq_rows:
            equipment_requirements_by_step_id.setdefault(eq.step_id, []).append(eq)

    vault_object = await vault_service.release_master(
        session,
        object_type="batch_execution_snapshot",
        business_id=str(batch.id),
        site_id=batch.site_id,
        actor_user_id=actor_user_id,
        business_version_label="1",
        canonical_payload={
            "batch_id": str(batch.id),
            "batch_number": batch.batch_number,
            "product_version_id": str(batch.product_version_id),
            "recipe_version_id": str(batch.recipe_version_id),
            "recipe_vault_object_id": str(batch.recipe_vault_object_id) if batch.recipe_vault_object_id else None,
            "target_qty": str(batch.target_qty),
            "target_uom": batch.target_uom,
            "steps": [
                {
                    "code": s.stable_step_code,
                    "step_type": s.step_type,
                    "sequence_hint": s.sequence_hint,
                    "initial_state": initial_states[s.stable_step_code],
                    # SG-178: freeze the recipe-declared performer role into the snapshot so step-start
                    # enforcement compares against the released recipe, not a later-mutated one.
                    "required_role_code": s.required_role_code,
                    # BAT-FR-014, SG-048 #014: same freeze-at-issue treatment for qualification.
                    "required_qualification_code": s.required_qualification_code,
                    # Known-limitations fix (docs/testing/demo-gujarati/08 §8.8): same treatment for
                    # equipment requirements.
                    "equipment_requirements": [
                        {
                            "equipment_class": eq.equipment_class,
                            "equipment_class_id": str(eq.equipment_class_id) if eq.equipment_class_id else None,
                            "exact_equipment_optional": eq.exact_equipment_optional,
                            "require_current_calibration": eq.require_current_calibration,
                            "require_current_qualification": eq.require_current_qualification,
                            "require_current_cleaning": eq.require_current_cleaning,
                        }
                        for eq in equipment_requirements_by_step_id.get(s.id, [])
                    ],
                }
                for s in steps
            ],
            "dependencies": [
                {"predecessor": code_by_step_id.get(d.predecessor_step_id), "successor": code_by_step_id.get(d.successor_step_id)}
                for d in dependencies
            ],
        },
    )
    batch.execution_snapshot_id = vault_object.object_id

    for s in steps:
        batch_step_id = uuid.uuid4()
        session.add(
            BatchStep(
                id=batch_step_id,
                batch_id=batch.id,
                recipe_step_code=s.stable_step_code,
                required_role_code=s.required_role_code,
                required_qualification_code=s.required_qualification_code,
                state=initial_states[s.stable_step_code],
            )
        )
        for eq in equipment_requirements_by_step_id.get(s.id, []):
            session.add(
                BatchStepEquipmentRequirement(
                    batch_step_id=batch_step_id,
                    equipment_class=eq.equipment_class,
                    equipment_class_id=eq.equipment_class_id,
                    exact_equipment_optional=eq.exact_equipment_optional,
                    require_current_calibration=eq.require_current_calibration,
                    require_current_qualification=eq.require_current_qualification,
                    require_current_cleaning=eq.require_current_cleaning,
                )
            )

    old_state = batch.state
    batch.state = "issued"
    batch.issued_at = datetime.now(timezone.utc)
    batch.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": batch.state, "execution_snapshot_id": str(vault_object.object_id), "step_count": len(steps)},
    )
    await write_outbox_event(
        session,
        event_type="BatchIssued",
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        payload={"id": str(batch.id), "execution_snapshot_id": str(vault_object.object_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="IssueBatch",
        aggregate_type="batch",
        aggregate_id=batch.id,
        expected_version=cmd.expected_version,
        resulting_version=batch.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=batch.id, resulting_version=batch.version, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


# ---------------------------------------------------------------------------
# Simple batch-state transitions — StartBatch/HoldBatch/ResumeBatch/AbortBatch (BAT-FR-004/019/020/031
# state-machine slice; reason capture goes to the audit event only -- gxp_batch_hold isn't DDL-ready,
# SG-047, so there's no dedicated hold record with its own signature this pass)
# ---------------------------------------------------------------------------


class BatchTransitionCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int
    reason: str | None = None


async def _simple_transition(
    session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID, *, new_state: str, command_type: str, event_type: str, action: str, timestamp_field: str | None = None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    _assert_transition(batch, new_state)
    old_state = batch.state
    batch.state = new_state
    batch.version += 1
    if timestamp_field:
        setattr(batch, timestamp_field, datetime.now(timezone.utc))

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        action=action,
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.reason,
        old_value={"state": old_state},
        new_value={"state": batch.state},
    )
    await write_outbox_event(
        session,
        event_type=event_type,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        payload={"id": str(batch.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type=command_type,
        aggregate_type="batch",
        aggregate_id=batch.id,
        expected_version=cmd.expected_version,
        resulting_version=batch.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=batch.id, resulting_version=batch.version, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


async def start_batch(session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(
        session, cmd, actor_user_id, new_state="in_execution", command_type="StartBatch", event_type="BatchStarted", action="Changed", timestamp_field="started_at"
    )


async def hold_batch(session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(
        session, cmd, actor_user_id, new_state="on_hold", command_type="HoldBatch", event_type="BatchHeld", action="Changed"
    )


async def resume_batch(session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(
        session, cmd, actor_user_id, new_state="in_execution", command_type="ResumeBatch", event_type="BatchResumed", action="Changed"
    )


async def abort_batch(session: AsyncSession, cmd: BatchTransitionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _simple_transition(
        session, cmd, actor_user_id, new_state="aborted", command_type="AbortBatch", event_type="BatchAborted", action="Changed"
    )


# ---------------------------------------------------------------------------
# StartStep — BAT-FR-007/008
# ---------------------------------------------------------------------------


class StartStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int
    # SG-178: only consulted when the step is reserved for a role the actor does not hold. A documented
    # reason plus the batch_step.role_override permission (Supervisor/Admin) lets a cross-trained actor
    # proceed; the reason is preserved in the audit event.
    override_reason: str | None = None
    # Known-limitations fix (docs/testing/demo-gujarati/08 §8.8): the specific EquipmentAsset(s) the actor
    # is using for this step, checked against the step's frozen equipment requirements in
    # _enforce_step_equipment(). Only consulted when the step actually declares a requirement.
    equipment_asset_ids: list[uuid.UUID] | None = None


async def _enforce_step_role(
    session: AsyncSession, *, step: BatchStep, batch: Batch, actor_user_id: uuid.UUID, override_reason: str | None
) -> bool:
    """SG-178 (BAT-FR-007). Returns True when the start proceeds under a documented role-override,
    False when the actor natively holds the step's declared role (or the step declares none).
    Raises StepRoleMismatchError otherwise.
    """
    required_role = step.required_role_code
    if not required_role:
        return False
    actor_roles = await effective_role_names(session, actor_user_id, batch.site_id)
    if required_role in actor_roles:
        return False
    if not override_reason or not override_reason.strip():
        raise StepRoleMismatchError(
            "This step is reserved for a role the actor does not hold; supply override_reason to proceed as a role-override",
            required_role_code=required_role,
            actor_roles=sorted(actor_roles),
        )
    try:
        await evaluate_policy(session, actor_user_id, action="batch_step.role_override", site_id=batch.site_id)
    except RoleMissingError:
        raise StepRoleMismatchError(
            "A role-mismatch override requires the batch_step.role_override permission (Supervisor/Admin)",
            required_role_code=required_role,
            actor_roles=sorted(actor_roles),
        )
    return True


async def _enforce_step_qualification(session: AsyncSession, *, step: BatchStep, actor_user_id: uuid.UUID) -> None:
    """BAT-FR-014, SG-048 #014 partial resolution. "Unqualified action blocked" -- unlike role, BAT-FR-014
    names no override path, so this fails closed with no override, checked at both start (performer) and
    complete (BAT-FR-014 also names "verifier", but no second-signer step type exists yet -- SG-048 #017 --
    so this pass applies the same performer check at both actions rather than guessing a verifier shape).
    Reuses `iam.qualifications` + the exact `material/commands.py::_check_dispensing_qualification`
    pattern (SG-086: two competing qualification stores exist, this picks the one with an already-reviewed
    production precedent and dedicated named error codes)."""
    required_code = step.required_qualification_code
    if not required_code:
        return
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Qualification)
        .where(Qualification.user_id == actor_user_id, Qualification.qualification_code == required_code)
        .order_by(Qualification.granted_at.desc())
        .limit(1)
    )
    qualification = result.scalar_one_or_none()
    if qualification is None:
        raise QualificationMissingError(
            "Actor has no record of the qualification this step requires", qualification_code=required_code
        )
    if qualification.expires_at is not None and qualification.expires_at.replace(tzinfo=timezone.utc) < now:
        raise QualificationExpiredError(
            "Actor's qualification for this step has expired", qualification_code=required_code
        )


# Reason codes that always block regardless of which require_current_* flags a requirement declares --
# an out-of-service or pending-post-maintenance-verification asset shouldn't be usable for any requirement.
_EQUIPMENT_ALWAYS_BLOCKING_CODES = {"EQUIPMENT_OUT_OF_SERVICE", "POST_MAINTENANCE_VERIFICATION_REQUIRED"}
_EQUIPMENT_REASON_ERRORS = {
    "EQUIPMENT_NOT_QUALIFIED": EquipmentNotQualifiedError,
    "CALIBRATION_EXPIRED": CalibrationExpiredError,
    "CALIBRATION_OOT_IMPACT_REQUIRED": CalibrationOotImpactRequiredError,
    "EQUIPMENT_OUT_OF_SERVICE": EquipmentOutOfServiceError,
    "POST_MAINTENANCE_VERIFICATION_REQUIRED": PostMaintenanceVerificationRequiredError,
    "CLEANING_REQUIRED": CleaningRequiredError,
}


async def _enforce_step_equipment(
    session: AsyncSession, *, step: BatchStep, equipment_asset_ids: list[uuid.UUID] | None
) -> list[EquipmentAsset]:
    """Known-limitations fix (docs/testing/demo-gujarati/08 §8.8, and this module's own docstring naming
    "Equipment master eligibility wiring" as not-yet-built). Compares the frozen
    `BatchStepEquipmentRequirement` rows for this step against the equipment_asset_ids the actor supplied
    at step-start, reusing `equipment.commands.get_eligibility()` (calibration_status/qualification_status/
    cleanliness_status) rather than reinventing equipment-currency logic -- only the reason codes relevant
    to the flags a requirement actually declares are blocking, plus EQUIPMENT_OUT_OF_SERVICE/post-
    maintenance-verification which always block regardless of flags.

    Returns the asset that satisfied each requirement, so the caller can persist a usage record
    (2026-09-19, project-owner-directed follow-up: eligibility was checked live here but never recorded
    anywhere, so review/release could never retrospectively see which equipment a batch actually used --
    see `EquipmentUseLog` writes in `start_step()` below)."""
    requirements = (
        await session.execute(
            select(BatchStepEquipmentRequirement).where(BatchStepEquipmentRequirement.batch_step_id == step.id)
        )
    ).scalars().all()
    if not requirements:
        return []

    supplied_ids = equipment_asset_ids or []
    assets: dict[uuid.UUID, EquipmentAsset] = {}
    for asset_id in supplied_ids:
        asset = await session.get(EquipmentAsset, asset_id)
        if asset is None:
            raise NotFoundError(
                "equipment_asset_ids references an equipment asset that does not exist", asset_id=str(asset_id)
            )
        assets[asset_id] = asset

    used: list[EquipmentAsset] = []
    for req in requirements:
        mandatory = req.require_current_calibration or req.require_current_qualification or req.require_current_cleaning or not req.exact_equipment_optional
        if req.equipment_class_id is not None:
            candidates = [a for a in assets.values() if a.equipment_class_id == req.equipment_class_id]
        else:
            # Legacy rows authored before the equipment-class-master fix have no controlled reference to
            # match against -- any supplied asset is accepted (equipment_class stays a captured label).
            candidates = list(assets.values())

        if not candidates:
            if not mandatory:
                continue
            if not supplied_ids:
                raise EquipmentRequirementNotMetError(
                    "This step requires equipment_asset_ids for a declared equipment requirement",
                    equipment_class=req.equipment_class,
                )
            raise EquipmentClassMismatchError(
                "None of the supplied equipment assets match this step's required equipment class",
                equipment_class=req.equipment_class,
            )

        asset = candidates[0]
        eligibility = await equipment_commands.get_eligibility(session, asset.id)
        relevant_codes = set(_EQUIPMENT_ALWAYS_BLOCKING_CODES)
        if req.require_current_calibration:
            relevant_codes |= {"CALIBRATION_OOT_IMPACT_REQUIRED", "CALIBRATION_EXPIRED"}
        if req.require_current_qualification:
            relevant_codes.add("EQUIPMENT_NOT_QUALIFIED")
        if req.require_current_cleaning:
            relevant_codes.add("CLEANING_REQUIRED")
        blocking = [r for r in eligibility["reasons"] if r["code"] in relevant_codes]
        if blocking:
            first = blocking[0]
            raise _EQUIPMENT_REASON_ERRORS[first["code"]](
                first["message"], asset_id=str(asset.id), equipment_class=req.equipment_class
            )
        used.append(asset)

    return used


async def start_step(session: AsyncSession, cmd: StartStepCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    if batch.state != "in_execution":
        raise ValidationFailedError("Steps can only be started while the batch is in_execution", current_state=batch.state)

    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)
    if step.state != "ready":
        raise InvalidTransitionError("Only a ready step can be claimed/started", current_state=step.state, requested="in_progress")

    role_override = await _enforce_step_role(
        session, step=step, batch=batch, actor_user_id=actor_user_id, override_reason=cmd.override_reason
    )
    await _enforce_step_qualification(session, step=step, actor_user_id=actor_user_id)
    used_equipment = await _enforce_step_equipment(session, step=step, equipment_asset_ids=cmd.equipment_asset_ids)
    for asset in used_equipment:
        # 2026-09-19, project-owner-directed: persist which asset satisfied this step's equipment
        # requirement -- previously checked live and discarded, so review/release had no way to
        # retrospectively see equipment that later went on hold or fell out of calibration/qualification
        # after this batch used it (`qa_review`/`release` service.py's `_equipment_signals`).
        session.add(
            EquipmentUseLog(
                equipment_asset_id=asset.id, site_id=batch.site_id, log_type="production",
                batch_id=batch.id, step_id=step.id, operator_user_id=actor_user_id, source="system",
                event_reference=step.recipe_step_code,
            )
        )

    step.state = "in_progress"
    step.assigned_subject_id = actor_user_id
    step.started_at = datetime.now(timezone.utc)
    step.version += 1

    new_value: dict = {"state": "in_progress"}
    if role_override:
        new_value.update(
            role_override=True,
            required_role_code=step.required_role_code,
            override_reason=cmd.override_reason,
        )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.override_reason if role_override else None,
        old_value={"state": "ready"},
        new_value=new_value,
    )
    await write_outbox_event(
        session,
        event_type="StepStarted",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={
            "id": str(step.id),
            "batch_id": str(batch.id),
            "recipe_step_code": step.recipe_step_code,
            "role_override": role_override,
        },
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="StartStep",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=audit_event.id, correlation_id=correlation_id
    )


# ---------------------------------------------------------------------------
# RecordStepResults / CompleteStep — BAT-FR-006 (runtime)/007/009/010/015/016
# SG-047 partial resolution (2026-09-09, project-owner-directed): the demo's own linear recipe
# (LC-01 -> ... -> HOLD-QA-01) got permanently stuck at BAT-FR-006's predecessor-only slice with no way
# to ever mark a step complete. This section adds gxp_step_result-backed result capture and a signed
# completion that advances the dependency graph. gxp_step_evidence_link/gxp_batch_hold, BAT-FR-023
# (correction), device/edge sourcing (BAT-FR-011) and the Production-Complete batch transition
# (BAT-FR-026) all stay out of scope -- see SG-047/SG-048, still open for those.
# ---------------------------------------------------------------------------


def _step_record_hash(step: BatchStep) -> str:
    return sha256_hex({"id": str(step.id), "version": step.version})


async def _require_step_signature(
    session: AsyncSession,
    *,
    step: BatchStep,
    action: str,
    challenge_id: uuid.UUID | None,
    reauth_password: str | None,
    actor_user_id: uuid.UUID,
) -> uuid.UUID | None:
    """Document 106 rows 19/21 (`batch_step`/`complete`, `batch_step`/`results`): both `Performed`,
    signer = the step's own qualified performer. That signer class is dynamic per step (Document 10's
    RecipeStep.required_role_code, frozen onto BatchStep at issue), which a single SignaturePolicy row
    can't express -- its own `required_role_id` is left NULL and `_enforce_step_role()` (SG-178, already
    applied at step start) covers it separately, called by the caller alongside this. No independence:
    the demo models independent verification as its own dedicated recipe step (e.g. ASSY-VER-01) rather
    than a second signer on the same action.
    """
    policy = await signature_service.resolve_signature_requirement(session, record_type="batch_step", action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError("This action requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session,
        challenge_id=challenge_id,
        user_id=actor_user_id,
        record_version=step.version,
        record_hash=_step_record_hash(step),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


async def _recipe_parameters_for_step(session: AsyncSession, batch: Batch, step: BatchStep) -> list[RecipeParameter]:
    graph = await recipe_master_service.get_graph(session, batch.recipe_version_id)
    code_by_step_id = {s.id: s.stable_step_code for s in graph["steps"]}
    step_id_by_code = {code: sid for sid, code in code_by_step_id.items()}
    recipe_step_id = step_id_by_code.get(step.recipe_step_code)
    return [p for p in graph["parameters"] if p.step_id == recipe_step_id]


async def _recipe_evidence_requirements_for_step(
    session: AsyncSession, batch: Batch, step: BatchStep
) -> list[RecipeEvidenceRequirement]:
    """BAT-FR-015 evidence half (SG-048 #015 partial resolution). Same lookup shape as
    `_recipe_parameters_for_step`, against the recipe's declared `gxp_recipe_evidence_requirement` rows
    instead of its parameters."""
    graph = await recipe_master_service.get_graph(session, batch.recipe_version_id)
    code_by_step_id = {s.id: s.stable_step_code for s in graph["steps"]}
    step_id_by_code = {code: sid for sid, code in code_by_step_id.items()}
    recipe_step_id = step_id_by_code.get(step.recipe_step_code)
    return [e for e in graph["evidence"] if e.step_id == recipe_step_id]



# BAT-FR-011, SG-048 #011 partial resolution: a human may tag a result 'device_transcribed' -- they read
# it off a device/instrument and are keying it in, distinct from their own direct observation ('manual').
# Both are still human-entered; true automated device/edge ingestion (registered source identity,
# sequence/idempotency, mapping version) is not built and stays SG-048 #011 open.
ALLOWED_RESULT_SOURCE_TYPES = ("manual", "device_transcribed")


def _step_result_quality_status(parameter: RecipeParameter, value_numeric: Decimal | None) -> str | None:
    """BAT-FR-009, SG-048 #009 partial resolution: informational only, never blocks the command (see
    StepResult.quality_status's own docstring for why)."""
    if parameter.min_value is None and parameter.max_value is None:
        return None
    if value_numeric is None:
        return "not_evaluated"
    if parameter.min_value is not None and value_numeric < parameter.min_value:
        return "out_of_range"
    if parameter.max_value is not None and value_numeric > parameter.max_value:
        return "out_of_range"
    return "in_range"


async def _auto_open_deviation_for_out_of_range(
    session: AsyncSession, *, batch: Batch, step: BatchStep, result: StepResult, actor_user_id: uuid.UUID
) -> None:
    """Known-limitations fix (docs/testing/demo-gujarati/08 §8.8 item 2), project-owner-directed
    2026-09-18: an in-process result outside its declared min/max previously stayed purely informational
    (StepResult.quality_status="out_of_range", nothing else) -- now it automatically opens a
    DeviationRecord instead of relying on a human noticing.

    Scope and shape were explicitly chosen by the project owner, not guessed:
    - Trigger: out-of-range in-process result ONLY (this pass). Step-hold and equipment-ineligibility
      triggers were explicitly deferred, not bundled in.
    - Auto-created in OPEN state with `owner_subject_id=None` -- a human (Supervisor/QA Reviewer) must
      triage and claim it at Investigation, same as `investigator_subject_id` already works. This is why
      `qms.deviation_record.owner_subject_id` became nullable (migration 9da2e9e4d481_0114).
    - `severity="minor"`, `deviation_type="process"` always -- conservative default; a human reclassifies
      at triage. Never auto-assigns an elevated severity.
    - `source_type="batch"`, `source_id=batch.id` (the existing generic SOURCE_TYPES pointer -- no
      dedicated step-level field exists on DeviationRecord, so the step/parameter identity is carried in
      the `reason` narrative instead, visible on the deviation's own "Created" audit event).

    Deliberately idempotent against duplicate submission the same way every other command in this
    module is: `deviation_number` is derived from the StepResult's own id (unique per result), so
    replaying the same idempotency key can never collide on `create_deviation`'s own
    UniqueConstraint("deviation_number") check.
    """
    cmd = qms_commands.CreateDeviationCommand(
        idempotency_key=f"auto-deviation-step-result-{result.id}",
        site_id=batch.site_id,
        deviation_number=f"DEV-AUTO-{batch.batch_number}-{step.recipe_step_code}-{result.id.hex[:8]}",
        deviation_type="process",
        source_type="batch",
        source_id=batch.id,
        severity="minor",
        owner_subject_id=None,
        reason=(
            f"Auto-opened: in-process result for parameter '{result.parameter_code}' on step "
            f"'{step.recipe_step_code}' (batch {batch.batch_number}) was out of range."
        ),
    )
    await qms_commands.create_deviation(session, cmd, actor_user_id)


class StepResultInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_code: str
    value_numeric: Decimal | None = None
    value_text: str | None = None
    value_bool: bool | None = None
    uom: str | None = None
    source_type: str = "manual"
    source_timestamp: datetime | None = None


class RecordStepResultsCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int
    results: list[StepResultInput]
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def record_step_results(
    session: AsyncSession, cmd: RecordStepResultsCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)
    if step.state != "in_progress":
        raise InvalidTransitionError(
            "Results can only be recorded against a step that is in progress", current_state=step.state
        )
    if not cmd.results:
        raise ValidationFailedError("At least one result is required")

    parameters_by_code = {p.parameter_code: p for p in await _recipe_parameters_for_step(session, batch, step)}
    for item in cmd.results:
        if item.parameter_code not in parameters_by_code:
            raise ValidationFailedError("Unknown parameter for this step", parameter_code=item.parameter_code)
        if item.source_type not in ALLOWED_RESULT_SOURCE_TYPES:
            raise ValidationFailedError(
                "Unknown source_type", source_type=item.source_type, allowed=list(ALLOWED_RESULT_SOURCE_TYPES)
            )

    signature_id = await _require_step_signature(
        session, step=step, action="results", challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id,
    )

    recorded: list[StepResult] = []
    out_of_range: list[StepResult] = []
    for item in cmd.results:
        parameter = parameters_by_code[item.parameter_code]
        quality_status = _step_result_quality_status(parameter, item.value_numeric)
        result = StepResult(
            id=uuid.uuid4(),
            step_id=step.id,
            parameter_code=item.parameter_code,
            data_type=parameter.data_type,
            value_numeric=item.value_numeric,
            value_text=item.value_text,
            value_bool=item.value_bool,
            uom=item.uom or parameter.uom,
            source_type=item.source_type,
            quality_status=quality_status,
            source_timestamp=item.source_timestamp,
            created_by=actor_user_id,
            signature_id=signature_id,
        )
        session.add(result)
        recorded.append(result)
        if quality_status == "out_of_range":
            out_of_range.append(result)

    # Every write against the batch_step aggregate bumps its version (MUT-FR-009) even though `state`
    # itself doesn't change here -- a concurrent second submission (or a stale `complete` call issued
    # before this one landed) then conflicts cleanly instead of silently racing.
    step.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"results_recorded": [r.parameter_code for r in recorded]},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="StepResultRecorded",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={
            "id": str(step.id),
            "batch_id": str(batch.id),
            "recipe_step_code": step.recipe_step_code,
            "parameter_codes": [r.parameter_code for r in recorded],
        },
        correlation_id=correlation_id,
    )

    # Known-limitations fix (docs/testing/demo-gujarati/08 §8.8 item 2): after the step-result write
    # itself is durable, auto-open a deviation for every out-of-range result -- same transaction, so a
    # DeviationRecord can never exist without the StepResult that caused it, or vice versa.
    for oor_result in out_of_range:
        await _auto_open_deviation_for_out_of_range(
            session, batch=batch, step=step, result=oor_result, actor_user_id=actor_user_id
        )

    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="RecordStepResults",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=audit_event.id,
        signature_id=signature_id, correlation_id=correlation_id,
    )


class EvidenceLinkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: uuid.UUID
    evidence_version: int = 1
    evidence_sha256: str
    media_type: str | None = None
    requirement_code: str | None = None


class LinkStepEvidenceCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int
    links: list[EvidenceLinkInput]


async def link_step_evidence(
    session: AsyncSession, cmd: LinkStepEvidenceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """SG-047 (`gxp_step_evidence_link` half). Unsigned by design -- Document 106 has no policy row for
    an "evidence link" action on `batch_step` (attaching evidence is a capture, not a release/disposition
    decision the way `complete`/`results` are); RBAC + audit is the same authorization level
    `evidence.upload` already uses elsewhere in this codebase."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)
    if step.state != "in_progress":
        raise InvalidTransitionError(
            "Evidence can only be linked against a step that is in progress", current_state=step.state
        )
    if not cmd.links:
        raise ValidationFailedError("At least one evidence link is required")

    linked: list[StepEvidenceLink] = []
    for item in cmd.links:
        link = StepEvidenceLink(
            step_id=step.id,
            evidence_id=item.evidence_id,
            evidence_version=item.evidence_version,
            evidence_sha256=item.evidence_sha256,
            media_type=item.media_type,
            requirement_code=item.requirement_code,
            linked_by=actor_user_id,
        )
        session.add(link)
        linked.append(link)

    # Same reasoning as record_step_results: bump the aggregate version even though `state` itself
    # doesn't change, so a concurrent write conflicts cleanly (MUT-FR-009).
    step.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"evidence_linked": [str(link.evidence_id) for link in linked]},
    )
    await write_outbox_event(
        session,
        event_type="StepEvidenceLinked",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={
            "id": str(step.id),
            "batch_id": str(batch.id),
            "recipe_step_code": step.recipe_step_code,
            "evidence_ids": [str(link.evidence_id) for link in linked],
        },
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="LinkStepEvidence",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class CompleteStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int
    # Same shape as StartStepCommand.override_reason (SG-178): only consulted when the actor doesn't hold
    # the step's declared role.
    override_reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_step(session: AsyncSession, cmd: CompleteStepCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    if batch.state != "in_execution":
        raise ValidationFailedError("Steps can only be completed while the batch is in_execution", current_state=batch.state)

    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)
    if step.state != "in_progress":
        raise InvalidTransitionError(
            "Only a step that is in progress can be completed", current_state=step.state, requested="complete"
        )

    role_override = await _enforce_step_role(
        session, step=step, batch=batch, actor_user_id=actor_user_id, override_reason=cmd.override_reason
    )
    await _enforce_step_qualification(session, step=step, actor_user_id=actor_user_id)

    # BAT-FR-015: every required RecipeParameter for this step must already have a recorded result.
    parameters = await _recipe_parameters_for_step(session, batch, step)
    required_codes = {p.parameter_code for p in parameters if p.required}
    if required_codes:
        recorded_codes = {r.parameter_code for r in await batch_execution_service.get_step_results(session, step.id)}
        missing = sorted(required_codes - recorded_codes)
        if missing:
            raise ParameterRequiredError("Required parameters have no recorded result", missing_parameter_codes=missing)

    # BAT-FR-015 evidence half (SG-048 #015 partial resolution, 2026-09-14): every RecipeEvidenceRequirement
    # declared for this step needs at least `required_count` StepEvidenceLink rows tagged with the
    # matching `requirement_code` (== the recipe's own `evidence_type` -- the same parameter_code<->
    # parameter_code naming symmetry the results check above already uses). Document 11 Section 7's own
    # named error vocabulary has no dedicated code for evidence-completeness (only PARAMETER_REQUIRED) --
    # this reuses the generic ValidationFailedError, the same class link_step_evidence already uses for
    # the sibling "at least one link is required" check, rather than inventing a new named error code.
    evidence_requirements = await _recipe_evidence_requirements_for_step(session, batch, step)
    if evidence_requirements:
        links = await batch_execution_service.get_step_evidence_links(session, step.id)
        linked_counts: dict[str, int] = {}
        for link in links:
            if link.requirement_code:
                linked_counts[link.requirement_code] = linked_counts.get(link.requirement_code, 0) + 1
        missing_evidence = sorted(
            req.evidence_type
            for req in evidence_requirements
            if linked_counts.get(req.evidence_type, 0) < req.required_count
        )
        if missing_evidence:
            raise ValidationFailedError("Required evidence has not been linked", missing_evidence_types=missing_evidence)

    signature_id = await _require_step_signature(
        session, step=step, action="complete", challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id,
    )

    old_state = step.state
    step.state = "complete"
    step.completed_at = datetime.now(timezone.utc)
    step.version += 1

    new_value: dict = {"state": "complete"}
    if role_override:
        new_value.update(role_override=True, required_role_code=step.required_role_code, override_reason=cmd.override_reason)

    correlation_id = uuid.uuid4()
    primary_audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.override_reason if role_override else None,
        old_value={"state": old_state},
        new_value=new_value,
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="StepCompleted",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={"id": str(step.id), "batch_id": str(batch.id), "recipe_step_code": step.recipe_step_code},
        correlation_id=correlation_id,
    )

    # BAT-FR-006 runtime half: a 'pending' successor becomes 'ready' once every one of its declared
    # predecessors is 'complete'. Each flip is its own audited version bump on that step's own aggregate.
    for ready_step in await batch_execution_service.recompute_readiness(session, batch):
        await write_audit_event(
            session,
            site_id=batch.site_id,
            aggregate_type="batch_step",
            aggregate_id=ready_step.id,
            aggregate_version=ready_step.version,
            action="Changed",
            actor_id=actor_user_id,
            correlation_id=correlation_id,
            old_value={"state": "pending"},
            new_value={"state": "ready"},
        )
        await write_outbox_event(
            session,
            event_type="StepReady",
            aggregate_type="batch_step",
            aggregate_id=ready_step.id,
            aggregate_version=ready_step.version,
            payload={"id": str(ready_step.id), "batch_id": str(batch.id), "recipe_step_code": ready_step.recipe_step_code},
            correlation_id=correlation_id,
        )

    # BAT-FR-026: the batch does NOT auto-transition to "production_complete" here even if this was the
    # last step -- that's its own explicit, separately signed action (production_complete_batch below),
    # matching every other batch lifecycle transition in this module (issue/start/hold/resume/abort are
    # all separate calls too, never implied by a step-level event).

    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="CompleteStep",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=primary_audit_event.id,
        signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# HoldStep / ResumeStep — BAT-FR-020, step scope (SG-047 further partial resolution, 2026-09-09)
# ---------------------------------------------------------------------------


class HoldStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


class ResumeStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def hold_step(session: AsyncSession, cmd: HoldStepCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    if batch.state != "in_execution":
        raise ValidationFailedError("Steps can only be held while the batch is in_execution", current_state=batch.state)

    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)
    if step.state != "in_progress":
        raise InvalidTransitionError("Only a step that is in progress can be held", current_state=step.state, requested="on_hold")
    if not cmd.reason or not cmd.reason.strip():
        raise ValidationFailedError("A hold reason is required")

    signature_id = await _require_step_signature(
        session, step=step, action="hold", challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id,
    )

    hold = StepHold(step_id=step.id, batch_id=batch.id, reason=cmd.reason, held_by=actor_user_id, hold_signature_id=signature_id)
    session.add(hold)

    old_state = step.state
    step.state = "on_hold"
    step.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.reason,
        old_value={"state": old_state},
        new_value={"state": "on_hold"},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="StepHeld",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={"id": str(step.id), "batch_id": str(batch.id), "recipe_step_code": step.recipe_step_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="HoldStep",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=audit_event.id,
        signature_id=signature_id, correlation_id=correlation_id,
    )


async def resume_step(session: AsyncSession, cmd: ResumeStepCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    if batch.state != "in_execution":
        raise ValidationFailedError("Steps can only be resumed while the batch is in_execution", current_state=batch.state)

    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)
    if step.state != "on_hold":
        raise InvalidTransitionError("Only a step that is on hold can be resumed", current_state=step.state, requested="in_progress")

    open_hold = (
        await session.execute(
            select(StepHold)
            .where(StepHold.step_id == step.id, StepHold.released_at.is_(None))
            .order_by(StepHold.held_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if open_hold is None:
        # Defensive -- the step being "on_hold" without an open StepHold row would mean the two records
        # disagree; fail closed rather than resume against nothing to release.
        raise ValidationFailedError("No active hold found for this step")

    signature_id = await _require_step_signature(
        session, step=step, action="resume", challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id,
    )

    open_hold.released_at = datetime.now(timezone.utc)
    open_hold.released_by = actor_user_id
    open_hold.release_reason = cmd.reason
    open_hold.release_signature_id = signature_id

    old_state = step.state
    step.state = "in_progress"
    step.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.reason,
        old_value={"state": old_state},
        new_value={"state": "in_progress"},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="StepResumed",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={"id": str(step.id), "batch_id": str(batch.id), "recipe_step_code": step.recipe_step_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="ResumeStep",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=audit_event.id,
        signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ProductionCompleteBatch — BAT-FR-026, steps-completeness sub-clause only (SG-048 #026 partial
# resolution, 2026-09-09)
# ---------------------------------------------------------------------------


class ProductionCompleteBatchCommand(CommandEnvelope):
    batch_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def production_complete_batch(
    session: AsyncSession, cmd: ProductionCompleteBatchCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await _load_batch_for_update(session, cmd.batch_id, cmd.expected_version)
    _assert_transition(batch, "production_complete")

    steps = await batch_execution_service.get_steps(session, batch.id)
    if not steps:
        raise ProductionNotCompleteError("Batch has no step instances yet")
    incomplete = sorted(s.recipe_step_code for s in steps if s.state != "complete")
    if incomplete:
        raise ProductionNotCompleteError("Not every batch step is complete", incomplete_step_codes=incomplete)

    policy = await signature_service.resolve_signature_requirement(session, record_type="batch", action="production_complete")
    signature_id = None
    if policy.signature_required:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError("Production-complete requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session,
            challenge_id=cmd.challenge_id,
            user_id=actor_user_id,
            record_version=batch.version,
            record_hash=_batch_record_hash(batch),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = batch.state
    batch.state = "production_complete"
    batch.production_completed_at = datetime.now(timezone.utc)
    batch.version += 1

    # 2026-09-19, project-owner-directed: Document 13 §8's own "DrugBatchProduced" event, wired directly.
    # Most batches already get their `drug_batch` node lazily the first time material is issued to them
    # (`material.commands.issue_material_to_batch`) -- this covers the batch that reached
    # production_complete without ever consuming a genealogy-tracked material lot, so every produced batch
    # is guaranteed a node regardless of material-consumption order.
    await genealogy_service.get_or_create_node(
        session, site_id=batch.site_id, node_type="drug_batch", authoritative_record_type="batch",
        authoritative_record_id=batch.id, business_ref=batch.batch_number, actor_user_id=actor_user_id,
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"state": old_state},
        new_value={"state": "production_complete"},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="ProductionCompleted",
        aggregate_type="batch",
        aggregate_id=batch.id,
        aggregate_version=batch.version,
        payload={"id": str(batch.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="ProductionCompleteBatch",
        aggregate_type="batch",
        aggregate_id=batch.id,
        expected_version=cmd.expected_version,
        resulting_version=batch.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=batch.id, resulting_version=batch.version, audit_event_id=audit_event.id,
        signature_id=signature_id, correlation_id=correlation_id,
    )


def _batch_record_hash(batch: Batch) -> str:
    return sha256_hex({"id": str(batch.id), "version": batch.version})


# ---------------------------------------------------------------------------
# RequestStepResultCorrection / ApproveStepResultCorrection -- BAT-FR-023, SG-048 #023 partial resolution
# (2026-09-14): POST /batches/{id}/steps/{stepId}/correct. 2-step, 2-signature per Document 106 row 20
# ("Authorized corrector + independent approver", corrector and approver MUST differ, mandatory reason).
# Deliberately mirrors qc.commands.request_result_correction/approve_result_correction (Document 106 row
# 57's identical shape) rather than inventing a new correction-ceremony pattern: a staging
# `StepResultCorrection` row holds the request between the two signed steps; approval appends a new
# `StepResult` row (`supersedes_result_id` set, `result_version` incremented) rather than editing the
# original -- AG-08. Scope kept to the literal requirement text ("Completed step data correction"): only a
# step already in state "complete" can have one of its results corrected.
# ---------------------------------------------------------------------------


def _step_result_hash(result: StepResult) -> str:
    return sha256_hex(
        {
            "id": str(result.id),
            "result_version": result.result_version,
            "value_numeric": str(result.value_numeric) if result.value_numeric is not None else None,
            "value_text": result.value_text,
            "value_bool": result.value_bool,
        }
    )


async def _require_step_result_signature(
    session: AsyncSession,
    *,
    result: StepResult,
    challenge_id: uuid.UUID | None,
    reauth_password: str | None,
    actor_user_id: uuid.UUID,
) -> uuid.UUID | None:
    """Document 106 row 20 (`batch_step_result`/`correct`): bound to the *original result's* own
    version/hash (never mutated across the request/approve pair, same precedent as
    qc.commands._record_hash(original, ..., version_field="result_version")), not the owning BatchStep's
    version -- the two are independent aggregates."""
    policy = await signature_service.resolve_signature_requirement(session, record_type="batch_step_result", action="correct")
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError("This action requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session,
        challenge_id=challenge_id,
        user_id=actor_user_id,
        record_version=result.result_version,
        record_hash=_step_result_hash(result),
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


class RequestStepResultCorrectionCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    result_id: uuid.UUID
    reason_text: str
    corrected_value_numeric: Decimal | None = None
    corrected_value_text: str | None = None
    corrected_value_bool: bool | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def request_step_result_correction(
    session: AsyncSession, cmd: RequestStepResultCorrectionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.reason_text:
        raise ValidationFailedError("reason_text is required for a step result correction")

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    step = await batch_execution_service.get_step(session, cmd.batch_id, cmd.step_id)
    if step.state != "complete":
        raise InvalidTransitionError(
            "Only a result on a completed step can be corrected", current_state=step.state
        )

    original = await session.get(StepResult, cmd.result_id)
    if original is None or original.step_id != step.id:
        raise NotFoundError("Step result not found")

    await evaluate_policy(session, actor_user_id, action="batch_step.correct", site_id=batch.site_id)

    signature_id = await _require_step_result_signature(
        session, result=original, challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id,
    )

    correction = StepResultCorrection(
        original_result_id=original.id,
        reason_text=cmd.reason_text,
        corrected_value_numeric=cmd.corrected_value_numeric,
        corrected_value_text=cmd.corrected_value_text,
        corrected_value_bool=cmd.corrected_value_bool,
        status="requested",
        requested_by_user_id=actor_user_id,
        requested_signature_id=signature_id,
    )
    session.add(correction)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="step_result_correction",
        aggregate_id=correction.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.reason_text,
        new_value={"original_result_id": str(original.id)},
        signature_id=signature_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="RequestStepResultCorrection",
        aggregate_type="step_result_correction",
        aggregate_id=correction.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=correction.id, resulting_version=1, audit_event_id=audit_event.id,
        signature_id=signature_id, correlation_id=correlation_id,
    )


class ApproveStepResultCorrectionCommand(CommandEnvelope):
    correction_id: uuid.UUID
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_step_result_correction(
    session: AsyncSession, cmd: ApproveStepResultCorrectionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    correction = await session.get(StepResultCorrection, cmd.correction_id)
    if correction is None:
        raise NotFoundError("Correction not found")
    if correction.status != "requested":
        raise InvalidTransitionError("Correction is not awaiting approval", current_status=correction.status)
    if actor_user_id == correction.requested_by_user_id:
        raise InvalidTransitionError("Approver must be independent of the corrector for this correction (SoD)")

    original = await session.get(StepResult, correction.original_result_id)
    step = await session.get(BatchStep, original.step_id)
    batch = await batch_execution_service.get_batch(session, step.batch_id)

    await evaluate_policy(session, actor_user_id, action="batch_step.correct", site_id=batch.site_id)

    signature_id = await _require_step_result_signature(
        session, result=original, challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id,
    )

    corrected_value_numeric = (
        correction.corrected_value_numeric if correction.corrected_value_numeric is not None else original.value_numeric
    )
    # BAT-FR-009, SG-048 #009: recompute quality_status for the corrected value, not the superseded one --
    # a correction that fixes an out-of-range reading should not keep carrying the old flag.
    parameters_by_code = {p.parameter_code: p for p in await _recipe_parameters_for_step(session, batch, step)}
    parameter = parameters_by_code.get(original.parameter_code)
    new_result = StepResult(
        step_id=original.step_id,
        parameter_code=original.parameter_code,
        data_type=original.data_type,
        result_version=original.result_version + 1,
        value_numeric=corrected_value_numeric,
        value_text=correction.corrected_value_text if correction.corrected_value_text is not None else original.value_text,
        value_bool=correction.corrected_value_bool if correction.corrected_value_bool is not None else original.value_bool,
        uom=original.uom,
        source_type=original.source_type,
        quality_status=_step_result_quality_status(parameter, corrected_value_numeric) if parameter else None,
        source_timestamp=original.source_timestamp,
        created_by=actor_user_id,
        signature_id=signature_id,
        supersedes_result_id=original.id,
    )
    session.add(new_result)
    await session.flush()

    correction.status = "completed"
    correction.approved_by_user_id = actor_user_id
    correction.approved_signature_id = signature_id
    correction.resulting_result_id = new_result.id
    correction.completed_at = datetime.now(timezone.utc)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="step_result_correction",
        aggregate_id=correction.id,
        aggregate_version=2,
        action="Approved",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"resulting_result_id": str(new_result.id)},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="StepResultCorrected",
        aggregate_type="batch_step_result",
        aggregate_id=new_result.id,
        aggregate_version=1,
        payload={"id": str(new_result.id), "step_id": str(step.id), "supersedes": str(original.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="ApproveStepResultCorrection",
        aggregate_type="step_result_correction",
        aggregate_id=correction.id,
        expected_version=None,
        resulting_version=2,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=new_result.id, resulting_version=1, audit_event_id=audit_event.id,
        signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# AddStepComment -- BAT-FR-034, SG-048 #034 partial resolution (2026-09-14): POST
# /batches/{id}/steps/{stepId}/comments. Unsigned by design -- Document 106 has no policy row for a
# comment action (a capture, not a release/disposition decision), same precedent as link_step_evidence.
# ---------------------------------------------------------------------------


class AddStepCommentCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int
    comment_text: str


async def add_step_comment(session: AsyncSession, cmd: AddStepCommentCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.comment_text or not cmd.comment_text.strip():
        raise ValidationFailedError("comment_text is required")

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)

    comment = StepComment(step_id=step.id, comment_text=cmd.comment_text, created_by=actor_user_id)
    session.add(comment)

    # Same reasoning as link_step_evidence: bump the aggregate version even though `state` itself doesn't
    # change, so a concurrent write conflicts cleanly (MUT-FR-009).
    step.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"comment_added": cmd.comment_text},
    )
    await write_outbox_event(
        session,
        event_type="StepCommentAdded",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={"id": str(step.id), "batch_id": str(batch.id), "recipe_step_code": step.recipe_step_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="AddStepComment",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# HandoverStep -- BAT-FR-025, SG-048 #025 partial resolution (2026-09-14, project-owner-directed: build
# unsigned/RBAC-gated interim scope). POST /batches/{id}/steps/{stepId}/handover. Unsigned -- no Document
# 106 policy row exists for this action; a real signature-policy decision for it is a human call this pass
# does not make (tracked in SG-048's own resolution note).
# ---------------------------------------------------------------------------


class HandoverStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    step_id: uuid.UUID
    expected_version: int
    to_user_id: uuid.UUID
    reason: str | None = None


async def handover_step(session: AsyncSession, cmd: HandoverStepCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await batch_execution_service.get_batch(session, cmd.batch_id)
    step = await _load_step_for_update(session, cmd.batch_id, cmd.step_id, cmd.expected_version)
    if step.state != "in_progress":
        raise InvalidTransitionError(
            "Only an in-progress step's working assignment can be handed over", current_state=step.state
        )

    to_user = await session.get(User, cmd.to_user_id)
    if to_user is None:
        raise NotFoundError("to_user_id does not reference a known user")

    from_subject_id = step.assigned_subject_id
    handover = StepHandover(
        step_id=step.id,
        from_subject_id=from_subject_id,
        to_subject_id=cmd.to_user_id,
        reason=cmd.reason,
        handed_over_by=actor_user_id,
    )
    session.add(handover)

    # "without changing prior attribution": step.started_at and the original StepStarted audit event are
    # untouched -- only the current working assignment moves forward, with its own full history here.
    step.assigned_subject_id = cmd.to_user_id
    step.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=batch.site_id,
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        reason=cmd.reason,
        old_value={"assigned_subject_id": str(from_subject_id) if from_subject_id else None},
        new_value={"assigned_subject_id": str(cmd.to_user_id)},
    )
    await write_outbox_event(
        session,
        event_type="StepHandedOver",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        aggregate_version=step.version,
        payload={
            "id": str(step.id), "batch_id": str(batch.id), "recipe_step_code": step.recipe_step_code,
            "from_subject_id": str(from_subject_id) if from_subject_id else None, "to_subject_id": str(cmd.to_user_id),
        },
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=batch.site_id,
        command_type="HandoverStep",
        aggregate_type="batch_step",
        aggregate_id=step.id,
        expected_version=cmd.expected_version,
        resulting_version=step.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=step.id, resulting_version=step.version, audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )
