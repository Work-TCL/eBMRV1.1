"""Document 55 (SPEC-DDCP-002, INJ-FR-001..030) — Autoinjector, Pen Injector & Cartridge-Based DDCP
Manufacturing Profile.

SG-150: no Document 112 schema exists for this document. Per the DDCP Platform Rule ("configure and extend
the common engines... shall not fork core GxP services"), this module reuses Document 54's own tables and
command functions wherever the concept is genuinely the same:

- Profile authoring/release: `ddcp_profile_version`/`constituent_requirement` (same tables, own subtype
  vocabulary `INJECTOR_SUBTYPES`, own create function below; `release_injectable_profile_version()` from
  `commands.py` is reused verbatim -- it is already fully generic, no PFS-specific vocabulary).
- Subassembly handoff (INJ-FR-004): `record_constituent_handoff()`/`decide_constituent_handoff()` from
  `commands.py`, reused verbatim -- also already fully generic.
- Assembly-step tracking (INJ-FR-007/010): `device_assembly_record`/`record_device_assembly_step()`,
  reused verbatim -- `ASSEMBLY_STEPS` extended with this document's own step vocabulary (SG-150).
- Functional/QC test linkage (INJ-FR-012..017): `device_functional_test_link`, reused verbatim --
  `test_type` was already an unenforced documented set.
- Release checkpoints / evidence manifest: `ddcp_release_checkpoint`/`batch_evidence_manifest`, reused
  verbatim -- the same three checkpoint codes generalize across every DDCP document.

Genuinely new for this document (SG-150): `ddcp_process_operation` (INJ-FR-006/007, the injector assembly
run), `ddcp_unit_binding` (INJ-FR-008/009, drug-container-to-injector-unit binding) and
`reusable_device_pairing` (INJ-FR-018).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch
from app.modules.ddcp.commands import (
    _assert_product_version_for_profile,
    _receipt_from_existing,
    _write_receipt,
)
from app.modules.ddcp.models import (
    INJECTOR_SUBTYPES,
    PAIRING_COMPATIBILITY_STATES,
    RELEASE_CHECKPOINT_CODES,
    BatchEvidenceManifest,
    ConstituentHandoff,
    ConstituentRequirement,
    DdcpProcessOperation,
    DdcpProfileVersion,
    DdcpReleaseCheckpoint,
    DdcpUnitBinding,
    DeviceAssemblyRecord,
    DeviceFunctionalTestLink,
    ReusableDevicePairing,
)
from app.modules.equipment.models import EquipmentAsset
from app.modules.rules import commands as rules_commands
from app.modules.rules.models import RuleEvaluation
from app.mutation.errors import (
    ContainerAlreadyUsedError,
    InjectorProfileNotEffectiveError,
    InvalidTransitionError,
    NotFoundError,
    ProfileSchemaInvalidError,
    ReworkRouteRequiredError,
    UnitReconciliationFailedError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

# ---------------------------------------------------------------------------------------------------
# DdcpProfileVersion — INJ-FR-001/002/003/028/029. createInjectorProfileVersion().
# release_injectable_profile_version() from commands.py is reused verbatim (already fully generic).
# ---------------------------------------------------------------------------------------------------


class CreateInjectorProfileVersionCommand(CommandEnvelope):
    site_id: uuid.UUID
    profile_code: str
    product_version_id: uuid.UUID  # SG-175 -- must be a RELEASED product version at this site
    injector_type: str  # INJECTOR_SUBTYPES
    device_bom_version_id: str | None = None
    unit_serialization: bool = False
    constituent_architecture: dict = {}
    required_controls: dict = {}
    release_checkpoint_set: dict = {"checkpoints": list(RELEASE_CHECKPOINT_CODES)}
    constituent_requirements: list[dict] = []


async def create_injector_profile_version(
    session: AsyncSession, cmd: CreateInjectorProfileVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.injector_type not in INJECTOR_SUBTYPES:
        raise ProfileSchemaInvalidError("Unrecognized injector_type", allowed=list(INJECTOR_SUBTYPES))
    for req in cmd.constituent_requirements:
        if not req.get("component_role"):
            raise ProfileSchemaInvalidError("Every constituent_requirement needs a component_role")
    # No manufacturing_profile_code names "autoinjector" (SG-175 residual half) -- existence/released/
    # site checked, family-match not.
    await _assert_product_version_for_profile(
        session, product_version_id=cmd.product_version_id, site_id=cmd.site_id,
        expected_manufacturing_profile_code=None,
    )

    next_version = (
        await session.execute(
            select(func.max(DdcpProfileVersion.version)).where(
                DdcpProfileVersion.site_id == cmd.site_id, DdcpProfileVersion.profile_code == cmd.profile_code,
            )
        )
    ).scalar() or 0

    profile = DdcpProfileVersion(
        site_id=cmd.site_id, profile_code=cmd.profile_code, product_version_id=cmd.product_version_id,
        subtype=cmd.injector_type, version=next_version + 1,
        state="DRAFT", constituent_architecture={
            "unitSerialization": cmd.unit_serialization, "deviceBOMVersionId": cmd.device_bom_version_id,
            **cmd.constituent_architecture,
        },
        required_controls=cmd.required_controls, release_checkpoint_set=cmd.release_checkpoint_set,
    )
    session.add(profile)
    await session.flush()

    for i, req in enumerate(cmd.constituent_requirements):
        session.add(ConstituentRequirement(
            site_id=cmd.site_id, ddcp_profile_version_id=profile.id, constituent_type=req["constituent_type"],
            component_role=req["component_role"], required_state=req.get("required_state", "RELEASED"),
            material_spec_reference=req.get("material_spec_reference"), attribute_requirements=req.get("attribute_requirements"),
            mandatory=req.get("mandatory", True), sequence_no=req.get("sequence_no", i),
        ))
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="ddcp_profile_version",
        aggregate_id=profile.id, version=profile.version, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="InjectorProfileDraftCreated",
        event_payload={"id": str(profile.id), "profile_code": profile.profile_code, "version": profile.version},
        expected_version=None, command_type="CreateInjectorProfileVersion",
    )


# ---------------------------------------------------------------------------------------------------
# Assembly readiness — INJ-FR-005/006. Pure read, mirrors evaluate_injectable_batch_readiness's shape.
# ---------------------------------------------------------------------------------------------------


async def evaluate_injector_assembly_readiness(
    session: AsyncSession, *, batch_id: uuid.UUID, profile_version_id: uuid.UUID,
) -> dict:
    profile = await session.get(DdcpProfileVersion, profile_version_id)
    if profile is None or profile.state != "RELEASED":
        raise InjectorProfileNotEffectiveError("Injector profile version is not RELEASED / effective", profile_version_id=str(profile_version_id))

    requirements = (
        await session.execute(select(ConstituentRequirement).where(ConstituentRequirement.ddcp_profile_version_id == profile_version_id, ConstituentRequirement.mandatory == True))  # noqa: E712
    ).scalars().all()
    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    accepted_roles = {h.to_constituent for h in handoffs if h.state == "ACCEPTED"}

    blockers = []
    for req in requirements:
        if req.component_role not in accepted_roles:
            code = "DRUG_CONTAINER_NOT_RELEASED" if req.constituent_type in ("DRUG", "BIOLOGIC") else "DEVICE_COMPONENT_NOT_RELEASED"
            blockers.append({"code": code, "message": f"No accepted handoff for required component_role '{req.component_role}'", "component_role": req.component_role})

    return {"batch_id": str(batch_id), "profile_version_id": str(profile_version_id), "ready": not blockers, "blockers": blockers}


# ---------------------------------------------------------------------------------------------------
# DdcpProcessOperation (operation_type=INJECTOR_ASSEMBLY) — INJ-FR-006/007. No dedicated "start" function
# is named in Document 55's own 9-function catalogue, but recordAssemblyParameter()'s own precondition
# ("Active assembly operation") requires one to exist -- derived the same way Document 54's
# DeviceAssemblyRecord commands were derived for an entity with no named writer.
# ---------------------------------------------------------------------------------------------------


class StartInjectorAssemblyOperationCommand(CommandEnvelope):
    batch_id: uuid.UUID
    profile_version_id: uuid.UUID
    line_id: uuid.UUID | None = None
    equipment_id: uuid.UUID | None = None
    program_id: str | None = None
    program_version: str | None = None


async def start_injector_assembly_operation(
    session: AsyncSession, cmd: StartInjectorAssemblyOperationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    readiness = await evaluate_injector_assembly_readiness(session, batch_id=cmd.batch_id, profile_version_id=cmd.profile_version_id)
    if not readiness["ready"]:
        raise ValidationFailedError("Injector assembly readiness is not satisfied", blockers=readiness["blockers"])

    if cmd.equipment_id is not None and await session.get(EquipmentAsset, cmd.equipment_id) is None:
        raise NotFoundError("Referenced equipment asset not found")

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    active = (
        await session.execute(
            select(DdcpProcessOperation).where(
                DdcpProcessOperation.batch_id == cmd.batch_id, DdcpProcessOperation.operation_type == "INJECTOR_ASSEMBLY",
                DdcpProcessOperation.state.in_(("SETUP", "EXECUTION", "HOLD")),
            )
        )
    ).scalar_one_or_none()
    if active is not None:
        raise InvalidTransitionError("Batch already has an active injector assembly operation", existing_operation_id=str(active.id))

    operation = DdcpProcessOperation(
        site_id=batch.site_id, batch_id=cmd.batch_id, operation_type="INJECTOR_ASSEMBLY", line_id=cmd.line_id,
        equipment_id=cmd.equipment_id, program_id=cmd.program_id, program_version=cmd.program_version,
        process_parameters={}, readiness_reference=readiness, started_at=datetime.now(timezone.utc), state="EXECUTION", version=1,
    )
    session.add(operation)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="ddcp_process_operation",
        aggregate_id=operation.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="InjectorAssemblyOperationStarted", event_payload={"id": str(operation.id), "batch_id": str(cmd.batch_id)},
        expected_version=None, command_type="StartInjectorAssemblyOperation",
    )


async def _load_operation_for_update(session: AsyncSession, operation_id: uuid.UUID, expected_version: int) -> DdcpProcessOperation:
    result = await session.execute(select(DdcpProcessOperation).where(DdcpProcessOperation.id == operation_id).with_for_update())
    operation = result.scalar_one_or_none()
    if operation is None:
        raise NotFoundError("Injector assembly operation not found")
    if operation.version != expected_version:
        from app.mutation.errors import StaleVersionError
        raise StaleVersionError("Operation was modified since it was read", expected_version=expected_version, current_version=operation.version)
    return operation


# ---------------------------------------------------------------------------------------------------
# bindDrugContainerToInjectorUnit() — INJ-FR-008/009. ddcp_unit_binding, binding_type=
# DRUG_CONTAINER_TO_INJECTOR_UNIT. Application-level uniqueness on the drug_container reference prevents
# CONTAINER_ALREADY_USED (SG-150, same JSONB-uniqueness-in-code discipline as ConstituentHandoff).
# ---------------------------------------------------------------------------------------------------


class BindDrugContainerToInjectorUnitCommand(CommandEnvelope):
    batch_id: uuid.UUID
    drug_container_reference: dict  # {"container_id": ...} or {"lot_id": ..., "unit_no": ...}
    injector_unit_serial: str


async def bind_drug_container_to_injector_unit(
    session: AsyncSession, cmd: BindDrugContainerToInjectorUnitCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    container_key = cmd.drug_container_reference.get("container_id") or cmd.drug_container_reference.get("lot_id")
    existing_bindings = (
        await session.execute(
            select(DdcpUnitBinding).where(DdcpUnitBinding.binding_type == "DRUG_CONTAINER_TO_INJECTOR_UNIT", DdcpUnitBinding.state == "BOUND")
        )
    ).scalars().all()
    for b in existing_bindings:
        existing_key = b.bound_constituent_reference.get("container_id") or b.bound_constituent_reference.get("lot_id")
        if existing_key == container_key:
            raise ContainerAlreadyUsedError("Drug container is already bound to another injector unit", drug_container_reference=cmd.drug_container_reference, existing_binding_id=str(b.id))

    binding = DdcpUnitBinding(
        site_id=batch.site_id, batch_id=cmd.batch_id, binding_type="DRUG_CONTAINER_TO_INJECTOR_UNIT",
        primary_unit_reference={"injector_unit_serial": cmd.injector_unit_serial}, bound_constituent_reference=cmd.drug_container_reference,
        state="BOUND", bound_by=actor_user_id, bound_at=datetime.now(timezone.utc), version=1,
    )
    session.add(binding)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="ddcp_unit_binding",
        aggregate_id=binding.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="DrugContainerBound", event_payload={"id": str(binding.id), "injector_unit_serial": cmd.injector_unit_serial},
        expected_version=None, command_type="BindDrugContainerToInjectorUnit",
    )


# ---------------------------------------------------------------------------------------------------
# recordAssemblyParameter() — INJ-FR-007. Appends to the active operation's process_parameters JSONB,
# the same append-in-place-JSONB-array pattern FillOperation.interventions already uses.
# ---------------------------------------------------------------------------------------------------


class RecordAssemblyParameterCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    parameter_code: str
    value: str
    uom: str | None = None
    source: str = "MANUAL"


async def record_assembly_parameter(
    session: AsyncSession, cmd: RecordAssemblyParameterCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state not in ("EXECUTION", "HOLD"):
        raise InvalidTransitionError("Assembly parameters can only be recorded while the operation is executing", current_state=operation.state)

    entry = {
        "parameter_code": cmd.parameter_code, "value": cmd.value, "uom": cmd.uom, "source": cmd.source,
        "actor_user_id": str(actor_user_id), "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    old_state = operation.state
    operation.process_parameters = {"readings": [*(operation.process_parameters or {}).get("readings", []), entry]}
    operation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="ddcp_process_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type="InjectorAssemblyParameterRecorded",
        event_payload={"id": str(operation.id), "parameter_code": cmd.parameter_code}, expected_version=cmd.expected_version,
        command_type="RecordAssemblyParameter",
    )


# ---------------------------------------------------------------------------------------------------
# executeInjectorFunctionalTest() — INJ-FR-012..017. Reuses device_functional_test_link verbatim.
# ---------------------------------------------------------------------------------------------------


class ExecuteInjectorFunctionalTestCommand(CommandEnvelope):
    batch_id: uuid.UUID
    test_type: str
    qc_record_reference: dict
    sample_plan_reference: dict | None = None
    method_reference: dict | None = None
    result_state: str = "PENDING"


async def execute_injector_functional_test(
    session: AsyncSession, cmd: ExecuteInjectorFunctionalTestCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    link = DeviceFunctionalTestLink(
        site_id=batch.site_id, batch_id=cmd.batch_id, test_type=cmd.test_type, qc_record_reference=cmd.qc_record_reference,
        sample_plan_reference=cmd.sample_plan_reference, method_reference=cmd.method_reference, result_state=cmd.result_state,
        blocks_release=cmd.result_state != "PASS", linked_at=datetime.now(timezone.utc), version=1,
    )
    session.add(link)
    await session.flush()

    event_type = "INJECTOR_TEST_FAILED" if cmd.result_state in ("FAIL", "OOS") else "InjectorFunctionalTestCompleted"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type=event_type, event_payload={"id": str(link.id), "test_type": link.test_type, "result_state": link.result_state},
        expected_version=None, command_type="ExecuteInjectorFunctionalTest",
    )


# ---------------------------------------------------------------------------------------------------
# evaluateDoseDeliveryResult() — INJ-FR-011/012/015. Same SG-148 rules-engine-evaluated pattern as
# Document 54's fill-weight IPC (PFS-FR-011): no dose-accuracy acceptance range is baselined anywhere,
# so the caller supplies a released rule id. Stores the result via device_functional_test_link
# (test_type=DOSE_ACCURACY), never a new table.
# ---------------------------------------------------------------------------------------------------


class EvaluateDoseDeliveryResultCommand(CommandEnvelope):
    batch_id: uuid.UUID
    sample_id: str
    actual_value: str  # decimal-as-string
    uom: str
    acceptance_rule_id: str
    qc_record_reference: dict = {}


async def evaluate_dose_delivery_result(
    session: AsyncSession, cmd: EvaluateDoseDeliveryResultCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    eval_receipt = await rules_commands.evaluate_rule(
        session,
        rules_commands.EvaluateRuleCommand(
            idempotency_key=f"{cmd.idempotency_key}:rule-eval", rule_id=cmd.acceptance_rule_id, inputs={"value": cmd.actual_value},
            aggregate_type="batch", aggregate_id=cmd.batch_id, aggregate_version=None,
        ),
        actor_user_id,
    )
    evaluation = await session.get(RuleEvaluation, eval_receipt.aggregate_id)
    outcome = evaluation.outcome if evaluation else "ERROR"
    result_state = "PASS" if outcome != "FAIL" else "FAIL"

    link = DeviceFunctionalTestLink(
        site_id=batch.site_id, batch_id=cmd.batch_id, test_type="DOSE_ACCURACY",
        qc_record_reference={**cmd.qc_record_reference, "sample_id": cmd.sample_id, "rule_evaluation_id": str(eval_receipt.aggregate_id)},
        result_state=result_state, blocks_release=result_state != "PASS", linked_at=datetime.now(timezone.utc), version=1,
    )
    session.add(link)
    await session.flush()

    event_type = "DOSE_DELIVERY_FAILED" if result_state == "FAIL" else "DoseDeliveryEvaluated"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type=event_type, event_payload={"id": str(link.id), "result_state": result_state, "rule_evaluation_id": str(eval_receipt.aggregate_id)},
        expected_version=None, command_type="EvaluateDoseDeliveryResult",
    )


# ---------------------------------------------------------------------------------------------------
# recordUnitDisposition() — INJ-FR-021/022. Reuses device_assembly_record with assembly_step=
# FINAL_DISPOSITION; REWORK/REJECT both require an explicit reference (INJ-FR-022's own "only through
# released route" / "unless procedure explicitly permits" text -- same default-disallow discipline as
# PFS-FR-027, reusing the same ReworkRouteRequiredError).
# ---------------------------------------------------------------------------------------------------


class RecordUnitDispositionCommand(CommandEnvelope):
    batch_id: uuid.UUID
    unit_identifier: str
    result: str  # PASS | REJECT | REWORK
    reason: str | None = None
    ncr_reference: dict | None = None
    rework_procedure_reference: dict | None = None


async def record_unit_disposition(
    session: AsyncSession, cmd: RecordUnitDispositionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.result not in ("PASS", "REJECT", "REWORK"):
        raise ValidationFailedError("result must be PASS, REJECT or REWORK")
    if cmd.result in ("REJECT", "REWORK") and not cmd.reason:
        raise ValidationFailedError("reason is required for a REJECT or REWORK disposition")
    if cmd.result == "REWORK" and not cmd.rework_procedure_reference:
        raise ReworkRouteRequiredError("Device rework is disallowed by default (INJ-FR-022) -- an explicit released-procedure reference is required")

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    record = DeviceAssemblyRecord(
        site_id=batch.site_id, batch_id=cmd.batch_id, unit_identifier=cmd.unit_identifier, assembly_step="FINAL_DISPOSITION",
        component_lot_reference={}, process_parameters={"reason": cmd.reason, "ncr_reference": cmd.ncr_reference, "rework_procedure_reference": cmd.rework_procedure_reference},
        performed_by=actor_user_id, result=cmd.result, occurred_at=datetime.now(timezone.utc), version=1,
    )
    session.add(record)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_assembly_record",
        aggregate_id=record.id, version=1, action="Created", actor_user_id=actor_user_id, reason=cmd.reason, old_state=None,
        event_type="InjectorUnitDispositioned", event_payload={"id": str(record.id), "unit_identifier": cmd.unit_identifier, "result": cmd.result},
        expected_version=None, command_type="RecordUnitDisposition",
    )


# ---------------------------------------------------------------------------------------------------
# completeInjectorAssemblyBatch() — INJ-FR-006/007/025. Structural completeness only (no numeric
# reconciliation tolerance baselined anywhere -- same SG-148 posture as Document 54's own
# complete_filling_stage): at least one ASSEMBLED unit recorded, no unresolved hold.
# ---------------------------------------------------------------------------------------------------


class CompleteInjectorAssemblyOperationCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    reason: str | None = None


async def complete_injector_assembly_operation(
    session: AsyncSession, cmd: CompleteInjectorAssemblyOperationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state != "EXECUTION":
        if operation.state == "HOLD":
            raise UnitReconciliationFailedError("Assembly operation has an unresolved hold")
        raise InvalidTransitionError("Only an executing assembly operation can be completed", current_state=operation.state)

    from app.modules.ddcp.models import ProductionCountLedger
    assembled_count = (
        await session.execute(
            select(func.coalesce(func.sum(ProductionCountLedger.quantity), 0)).where(
                ProductionCountLedger.batch_id == operation.batch_id, ProductionCountLedger.count_type == "ASSEMBLED",
            )
        )
    ).scalar()
    if not assembled_count:
        raise UnitReconciliationFailedError("No ASSEMBLED units recorded for this batch -- reconciliation is not constructible")

    old_state = operation.state
    operation.state = "COMPLETE"
    operation.ended_at = datetime.now(timezone.utc)
    operation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="ddcp_process_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id, reason=cmd.reason,
        old_state=old_state, event_type="InjectorAssemblyCompleted", event_payload={"id": str(operation.id), "state": operation.state},
        expected_version=cmd.expected_version, command_type="CompleteInjectorAssemblyOperation",
    )


# ---------------------------------------------------------------------------------------------------
# evaluateInjectorReleaseReadiness() — INJ-FR-026/027. Same three-checkpoint composition as Document 54's
# evaluate_pfs_release_readiness, reusing ddcp_release_checkpoint verbatim.
# ---------------------------------------------------------------------------------------------------


async def evaluate_injector_release_readiness(session: AsyncSession, batch_id: uuid.UUID, actor_user_id: uuid.UUID) -> dict:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    drug_ok = any(h.from_constituent in ("DRUG", "BIOLOGIC") and h.state == "ACCEPTED" for h in handoffs)
    device_handoffs_pending = [h for h in handoffs if h.from_constituent == "DEVICE" and h.state != "ACCEPTED"]

    test_links = (
        await session.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch_id).order_by(DeviceFunctionalTestLink.linked_at))
    ).scalars().all()
    latest_by_test_type: dict[str, DeviceFunctionalTestLink] = {}
    for link in test_links:
        latest_by_test_type[link.test_type] = link
    failed_tests = [t for t in latest_by_test_type.values() if t.blocks_release and t.result_state != "PASS"]

    rejected_units = (
        await session.execute(select(func.count()).select_from(DeviceAssemblyRecord).where(DeviceAssemblyRecord.batch_id == batch_id, DeviceAssemblyRecord.result == "REJECT"))
    ).scalar()

    checkpoint_results: dict[str, dict] = {}
    checkpoint_results["DRUG_CONSTITUENT"] = (
        {"state": "SATISFIED", "blockers": []} if drug_ok
        else {"state": "BLOCKED", "blockers": [{"code": "DRUG_CONTAINER_NOT_RELEASED", "message": "No accepted drug/biologic handoff"}]}
    )
    device_blockers = []
    if device_handoffs_pending:
        device_blockers.append({"code": "DEVICE_COMPONENT_NOT_RELEASED", "message": f"{len(device_handoffs_pending)} device handoff(s) not accepted"})
    for test in failed_tests:
        device_blockers.append({"code": "INJECTOR_TEST_FAILED", "message": f"{test.test_type} result is {test.result_state}", "test_link_id": str(test.id)})
    checkpoint_results["DEVICE_CONSTITUENT"] = {"state": "SATISFIED", "blockers": []} if not device_blockers else {"state": "BLOCKED", "blockers": device_blockers}

    combined_blockers = list(checkpoint_results["DRUG_CONSTITUENT"]["blockers"]) + list(checkpoint_results["DEVICE_CONSTITUENT"]["blockers"])
    if rejected_units:
        combined_blockers.append({"code": "UNIT_GENEALOGY_INCOMPLETE", "message": f"{rejected_units} unit(s) have a REJECT disposition with no superseding release evidence"})
    checkpoint_results["COMBINED_PRODUCT"] = {"state": "SATISFIED", "blockers": []} if not combined_blockers else {"state": "BLOCKED", "blockers": combined_blockers}

    for code, outcome in checkpoint_results.items():
        existing_checkpoint = (
            await session.execute(select(DdcpReleaseCheckpoint).where(DdcpReleaseCheckpoint.batch_id == batch_id, DdcpReleaseCheckpoint.checkpoint_code == code))
        ).scalar_one_or_none()
        if existing_checkpoint is None:
            session.add(DdcpReleaseCheckpoint(
                site_id=batch.site_id, batch_id=batch_id, checkpoint_code=code, required_evidence={"blockers_at_creation": outcome["blockers"]},
                blocker_state={"blockers": outcome["blockers"]}, state=outcome["state"], version=1,
            ))
        else:
            if existing_checkpoint.state != "WAIVED_BY_APPROVAL":
                existing_checkpoint.blocker_state = {"blockers": outcome["blockers"]}
                existing_checkpoint.state = outcome["state"]
                existing_checkpoint.version += 1
    await session.flush()

    return {
        "batch_id": str(batch_id), "ready": all(v["state"] in ("SATISFIED", "WAIVED_BY_APPROVAL") for v in checkpoint_results.values()),
        "checkpoints": checkpoint_results,
    }


class CreateInjectorBatchEvidencePackageCommand(CommandEnvelope):
    batch_id: uuid.UUID


async def create_injector_batch_evidence_package(
    session: AsyncSession, cmd: CreateInjectorBatchEvidencePackageCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """INJ-FR-030 (evidence export). No dedicated function is named for this in Document 55's own 9-
    function catalogue (traceComplaintSerial() returns a graph but never freezes one) -- derived the same
    way Document 54's create_pfs_batch_evidence_package() was, reusing batch_evidence_manifest verbatim."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (await session.execute(select(ConstituentHandoff.id, ConstituentHandoff.version).where(ConstituentHandoff.batch_id == cmd.batch_id))).all()
    bindings = (await session.execute(select(DdcpUnitBinding.id, DdcpUnitBinding.version).where(DdcpUnitBinding.batch_id == cmd.batch_id))).all()
    assembly = (await session.execute(select(DeviceAssemblyRecord.id, DeviceAssemblyRecord.version).where(DeviceAssemblyRecord.batch_id == cmd.batch_id))).all()
    test_links = (await session.execute(select(DeviceFunctionalTestLink.id, DeviceFunctionalTestLink.version).where(DeviceFunctionalTestLink.batch_id == cmd.batch_id))).all()
    checkpoints = (await session.execute(select(DdcpReleaseCheckpoint.id, DdcpReleaseCheckpoint.version).where(DdcpReleaseCheckpoint.batch_id == cmd.batch_id))).all()

    evidence_set = {
        "constituent_handoffs": [{"id": str(i), "version": v} for i, v in handoffs],
        "ddcp_unit_bindings": [{"id": str(i), "version": v} for i, v in bindings],
        "device_assembly_records": [{"id": str(i), "version": v} for i, v in assembly],
        "device_functional_test_links": [{"id": str(i), "version": v} for i, v in test_links],
        "ddcp_release_checkpoints": [{"id": str(i), "version": v} for i, v in checkpoints],
    }
    digest = sha256_hex(evidence_set)

    next_version = (
        await session.execute(select(func.max(BatchEvidenceManifest.manifest_version)).where(BatchEvidenceManifest.batch_id == cmd.batch_id))
    ).scalar() or 0

    manifest = BatchEvidenceManifest(
        site_id=batch.site_id, batch_id=cmd.batch_id, manifest_version=next_version + 1, evidence_set=evidence_set,
        digest=digest, generated_by=actor_user_id, generated_at=datetime.now(timezone.utc), state="FROZEN", version=1,
    )
    session.add(manifest)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="batch_evidence_manifest",
        aggregate_id=manifest.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="InjectorBatchEvidencePackageGenerated", event_payload={"id": str(manifest.id), "manifest_version": manifest.manifest_version, "digest": digest},
        expected_version=None, command_type="CreateInjectorBatchEvidencePackage",
    )


# ---------------------------------------------------------------------------------------------------
# traceComplaintSerial() — INJ-FR-025/030. Pure read genealogy composition by finished serial (not
# batch_id), traversing device_assembly_record/ddcp_unit_binding/device_functional_test_link for that
# serial. No new table -- the underlying data already carries the serial-scoped references it needs.
# ---------------------------------------------------------------------------------------------------


async def trace_complaint_serial(session: AsyncSession, finished_serial: str) -> dict:
    assembly = (
        await session.execute(select(DeviceAssemblyRecord).where(DeviceAssemblyRecord.unit_identifier == finished_serial))
    ).scalars().all()
    if not assembly:
        raise NotFoundError("No device assembly record found for this serial")

    batch_ids = {a.batch_id for a in assembly}
    bindings = (
        await session.execute(select(DdcpUnitBinding).where(DdcpUnitBinding.primary_unit_reference["injector_unit_serial"].astext == finished_serial))
    ).scalars().all()
    test_links = (
        await session.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id.in_(batch_ids)))
    ).scalars().all()

    return {
        "finished_serial": finished_serial,
        "batch_ids": [str(b) for b in batch_ids],
        "device_assembly_records": [
            {"id": str(a.id), "assembly_step": a.assembly_step, "component_lot_reference": a.component_lot_reference, "result": a.result}
            for a in assembly
        ],
        "drug_container_bindings": [
            {"id": str(b.id), "bound_constituent_reference": b.bound_constituent_reference, "state": b.state}
            for b in bindings
        ],
        "functional_test_links": [
            {"id": str(t.id), "test_type": t.test_type, "result_state": t.result_state} for t in test_links
        ],
    }


# ---------------------------------------------------------------------------------------------------
# recordReusableDevicePairing() — INJ-FR-018. "For reusable injector + cartridge, model compatibility/
# approved pairing and cartridge lot genealogy without assuming permanent single unit relationship."
# No function is named for this in Document 55's own 9-function catalogue -- derived the same way
# Document 54's DeviceAssemblyRecord commands were derived for an entity with no named writer.
# `batch_id` is optional (see reusable_device_pairing's own docstring: a compatibility decision can
# predate any specific batch).
# ---------------------------------------------------------------------------------------------------


class RecordReusableDevicePairingCommand(CommandEnvelope):
    reusable_device_reference: dict
    cartridge_lot_reference: dict
    compatibility_status: str = "PENDING_REVIEW"
    rationale: str | None = None
    batch_id: uuid.UUID | None = None


async def record_reusable_device_pairing(
    session: AsyncSession, cmd: RecordReusableDevicePairingCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.compatibility_status not in PAIRING_COMPATIBILITY_STATES:
        raise ValidationFailedError("Unrecognized compatibility_status", allowed=list(PAIRING_COMPATIBILITY_STATES))

    site_id: uuid.UUID
    if cmd.batch_id is not None:
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        site_id = batch.site_id
    else:
        # No batch-independent site reference is named in Document 55 -- a pairing decision authored
        # ahead of any batch still needs a site scope (Document 70 universal aggregate baseline), so
        # the caller must supply one via a batch reference, or this is left NOT_STARTED for a truly
        # batch-independent authoring flow (see SG-150 update).
        raise ValidationFailedError("batch_id is required this pass -- a batch-independent pairing-authoring flow is not yet implemented (see SG-150)")

    pairing = ReusableDevicePairing(
        site_id=site_id, batch_id=cmd.batch_id, reusable_device_reference=cmd.reusable_device_reference,
        cartridge_lot_reference=cmd.cartridge_lot_reference, compatibility_status=cmd.compatibility_status,
        rationale=cmd.rationale, paired_by=actor_user_id, paired_at=datetime.now(timezone.utc), version=1,
    )
    session.add(pairing)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=site_id, aggregate_type="reusable_device_pairing",
        aggregate_id=pairing.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="ReusableDevicePairingRecorded", event_payload={"id": str(pairing.id), "compatibility_status": cmd.compatibility_status},
        expected_version=None, command_type="RecordReusableDevicePairing",
    )
