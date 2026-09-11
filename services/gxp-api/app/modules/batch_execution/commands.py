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
from app.modules.batch_execution.models import ALLOWED_TRANSITIONS, Batch, BatchStep, StepEvidenceLink, StepHold, StepResult
from app.modules.iam.models import User
from app.modules.policy.service import effective_role_names, evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.modules.recipe_master import service as recipe_master_service
from app.modules.recipe_master.models import RecipeParameter
from app.modules.rules import service as rules_service
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    ParameterRequiredError,
    ProductionNotCompleteError,
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
        target_uom_id=await _resolve_uom_id(session, cmd.target_uom),
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
        session.add(
            BatchStep(
                batch_id=batch.id,
                recipe_step_code=s.stable_step_code,
                required_role_code=s.required_role_code,
                state=initial_states[s.stable_step_code],
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


class StepResultInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_code: str
    value_numeric: Decimal | None = None
    value_text: str | None = None
    value_bool: bool | None = None
    uom: str | None = None
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

    signature_id = await _require_step_signature(
        session, step=step, action="results", challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
        actor_user_id=actor_user_id,
    )

    recorded: list[StepResult] = []
    for item in cmd.results:
        parameter = parameters_by_code[item.parameter_code]
        result = StepResult(
            step_id=step.id,
            parameter_code=item.parameter_code,
            data_type=parameter.data_type,
            value_numeric=item.value_numeric,
            value_text=item.value_text,
            value_bool=item.value_bool,
            uom=item.uom or parameter.uom,
            source_timestamp=item.source_timestamp,
            created_by=actor_user_id,
            signature_id=signature_id,
        )
        session.add(result)
        recorded.append(result)

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

    # BAT-FR-015: every required RecipeParameter for this step must already have a recorded result.
    parameters = await _recipe_parameters_for_step(session, batch, step)
    required_codes = {p.parameter_code for p in parameters if p.required}
    if required_codes:
        recorded_codes = {r.parameter_code for r in await batch_execution_service.get_step_results(session, step.id)}
        missing = sorted(required_codes - recorded_codes)
        if missing:
            raise ParameterRequiredError("Required parameters have no recorded result", missing_parameter_codes=missing)

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
