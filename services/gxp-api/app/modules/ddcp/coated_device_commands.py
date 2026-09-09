"""Document 57 (SPEC-DDCP-004, COAT-FR-001..030) — Drug-Eluting / Drug-Coated Device DDCP Manufacturing
Profile.

SG-150: no Document 112 schema exists for this document. Reuses Document 54's tables/functions per the
DDCP Platform Rule, the same reuse strategy `injector_commands.py`/`inhalation_commands.py` already apply:
`ddcp_profile_version`/`constituent_requirement` (COAT-FR-001 names no subtype variant of its own --
`subtype` stays unset), `constituent_handoff` (substrate/coating-drug handoffs), `device_assembly_record`
(surface-prep/coating-application/drying-curing steps), `device_functional_test_link` (drug-content-assay/
coating-integrity/release-elution/dimensional-function test types), `production_count_ledger` (device-unit
side of the dual reconciliation, count_type=COATED), `ddcp_release_checkpoint`, `batch_evidence_manifest`.
`ddcp_process_operation` (operation_type=COATING_RUN) is reused from Document 55. Two tables are genuinely
new for this document: `ddcp_unit_binding` (binding_type=DEVICE_TO_COATING_CONSTITUENT, shared with
Document 55's own binding_type) and `drug_coating_usage_ledger` (COAT-FR-009's decimal mass-balance side
of the dual reconciliation -- distinct from the integer unit-count ledger).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp.commands import _assert_product_version_for_profile, _receipt_from_existing, _write_receipt
from app.modules.ddcp.models import (
    COATING_USAGE_TYPES,
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
    DrugCoatingUsageLedger,
    ProductionCountLedger,
)
from app.modules.equipment.models import EquipmentAsset
from app.modules.rules import commands as rules_commands
from app.modules.rules.models import RuleEvaluation
from app.mutation.errors import (
    CoatedDeviceProfileNotEffectiveError,
    CoatingReconciliationFailedError,
    DeviceToCoatingBindingAlreadyUsedError,
    InvalidTransitionError,
    NotFoundError,
    ProfileSchemaInvalidError,
    ReworkRouteRequiredError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


# ---------------------------------------------------------------------------------------------------
# DdcpProfileVersion — COAT-FR-001/002/003/005. createCoatedDeviceProfileVersion().
# release_injectable_profile_version() from commands.py is reused verbatim.
# ---------------------------------------------------------------------------------------------------


class CreateCoatedDeviceProfileVersionCommand(CommandEnvelope):
    site_id: uuid.UUID
    profile_code: str
    product_version_id: uuid.UUID  # SG-175 -- must be a RELEASED product version at this site
    coating_route_id: str | None = None
    sterilization_route_id: str | None = None
    environment_profile_id: str | None = None
    constituent_architecture: dict = {}
    required_controls: dict = {}
    release_checkpoint_set: dict = {"checkpoints": list(RELEASE_CHECKPOINT_CODES)}
    constituent_requirements: list[dict] = []


async def create_coated_device_profile_version(
    session: AsyncSession, cmd: CreateCoatedDeviceProfileVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    for req in cmd.constituent_requirements:
        if not req.get("component_role"):
            raise ProfileSchemaInvalidError("Every constituent_requirement needs a component_role")
    # No manufacturing_profile_code names "coated device" specifically -- `drug_eluting_device` is only
    # an example subtype (SG-175 residual half) -- existence/released/site checked, family-match not.
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
        subtype=None, version=next_version + 1, state="DRAFT",
        constituent_architecture={
            "coatingRouteId": cmd.coating_route_id, "sterilizationRouteId": cmd.sterilization_route_id,
            "environmentProfileId": cmd.environment_profile_id, **cmd.constituent_architecture,
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
        old_state=None, event_type="CoatedDeviceProfileDraftCreated",
        event_payload={"id": str(profile.id), "profile_code": profile.profile_code, "version": profile.version},
        expected_version=None, command_type="CreateCoatedDeviceProfileVersion",
    )


# ---------------------------------------------------------------------------------------------------
# evaluateCoatingRunReadiness() — COAT-FR-002/003/004/007/008. Pure read; environment gate (COAT-FR-008)
# is a caller-supplied status snapshot, same restraint as Document 56's environment gate -- Document 57
# §7 itself: "No generic sterilization assumption is allowed", and §7's environment text has the same
# "product/validation-controlled, not generic constants" posture as Document 56 §7.
# ---------------------------------------------------------------------------------------------------


async def evaluate_coating_run_readiness(
    session: AsyncSession, *, batch_id: uuid.UUID, profile_version_id: uuid.UUID, environment_status: dict | None = None,
) -> dict:
    profile = await session.get(DdcpProfileVersion, profile_version_id)
    if profile is None or profile.state != "RELEASED":
        raise CoatedDeviceProfileNotEffectiveError("Coated device profile version is not RELEASED / effective", profile_version_id=str(profile_version_id))

    requirements = (
        await session.execute(select(ConstituentRequirement).where(ConstituentRequirement.ddcp_profile_version_id == profile_version_id, ConstituentRequirement.mandatory == True))  # noqa: E712
    ).scalars().all()
    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    accepted_roles = {h.to_constituent for h in handoffs if h.state == "ACCEPTED"}

    blockers = []
    for req in requirements:
        if req.component_role not in accepted_roles:
            code = "COATING_DRUG_NOT_RELEASED" if req.constituent_type in ("DRUG", "BIOLOGIC") else "SUBSTRATE_NOT_RELEASED"
            blockers.append({"code": code, "message": f"No accepted handoff for required component_role '{req.component_role}'", "component_role": req.component_role})

    environment_required = bool((profile.constituent_architecture or {}).get("environmentProfileId"))
    if environment_required and environment_status is not None and environment_status.get("ready") is False:
        blockers.append({"code": "COATING_ENVIRONMENT_NOT_READY", "message": "Environment status snapshot reports not ready", "environment_status": environment_status})

    return {"batch_id": str(batch_id), "profile_version_id": str(profile_version_id), "ready": not blockers, "blockers": blockers}


# ---------------------------------------------------------------------------------------------------
# Drug/coating usage ledger — COAT-FR-009. Decimal mass-balance ledger, distinct from
# production_count_ledger's integer unit counts (DATA-FR-019). record_drug_coating_usage() is the one
# writer, reused by startCoatingRun() (ISSUED) and completeCoatingRun() (APPLIED/RESIDUAL/etc).
# ---------------------------------------------------------------------------------------------------


class RecordDrugCoatingUsageCommand(CommandEnvelope):
    batch_id: uuid.UUID
    usage_type: str
    quantity: str  # decimal-as-string
    uom: str
    reason_code: str | None = None
    occurred_at: datetime | None = None


async def record_drug_coating_usage(
    session: AsyncSession, cmd: RecordDrugCoatingUsageCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.usage_type not in COATING_USAGE_TYPES:
        raise ValidationFailedError("Unrecognized usage_type", allowed=list(COATING_USAGE_TYPES))

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    entry = DrugCoatingUsageLedger(
        site_id=batch.site_id, batch_id=cmd.batch_id, usage_type=cmd.usage_type, quantity=Decimal(cmd.quantity), uom=cmd.uom,
        recorded_by=actor_user_id, reason_code=cmd.reason_code, occurred_at=cmd.occurred_at or datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="drug_coating_usage_ledger",
        aggregate_id=entry.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="DrugCoatingUsageRecorded", event_payload={"id": str(entry.id), "usage_type": cmd.usage_type, "quantity": cmd.quantity},
        expected_version=None, command_type="RecordDrugCoatingUsage",
    )


# ---------------------------------------------------------------------------------------------------
# startCoatingRun() — COAT-FR-005/006/007/008. Reuses DdcpProcessOperation (operation_type=COATING_RUN).
# ---------------------------------------------------------------------------------------------------


class StartCoatingRunCommand(CommandEnvelope):
    batch_id: uuid.UUID
    profile_version_id: uuid.UUID
    line_id: uuid.UUID | None = None
    equipment_id: uuid.UUID | None = None
    program_id: str | None = None
    program_version: str | None = None
    environment_status: dict | None = None
    initial_drug_solution_quantity: str | None = None  # decimal-as-string
    initial_drug_solution_uom: str | None = None


async def start_coating_run(
    session: AsyncSession, cmd: StartCoatingRunCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    readiness = await evaluate_coating_run_readiness(session, batch_id=cmd.batch_id, profile_version_id=cmd.profile_version_id, environment_status=cmd.environment_status)
    if not readiness["ready"]:
        raise ValidationFailedError("Coating run readiness is not satisfied", blockers=readiness["blockers"])

    if cmd.equipment_id is not None and await session.get(EquipmentAsset, cmd.equipment_id) is None:
        raise NotFoundError("Referenced equipment asset not found")

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    active = (
        await session.execute(
            select(DdcpProcessOperation).where(
                DdcpProcessOperation.batch_id == cmd.batch_id, DdcpProcessOperation.operation_type == "COATING_RUN",
                DdcpProcessOperation.state.in_(("SETUP", "EXECUTION", "HOLD")),
            )
        )
    ).scalar_one_or_none()
    if active is not None:
        raise InvalidTransitionError("Batch already has an active coating run", existing_operation_id=str(active.id))

    operation = DdcpProcessOperation(
        site_id=batch.site_id, batch_id=cmd.batch_id, operation_type="COATING_RUN", line_id=cmd.line_id,
        equipment_id=cmd.equipment_id, program_id=cmd.program_id, program_version=cmd.program_version,
        process_parameters={}, environment_reference=cmd.environment_status, readiness_reference=readiness,
        started_at=datetime.now(timezone.utc), state="EXECUTION", version=1,
    )
    session.add(operation)
    await session.flush()

    if cmd.initial_drug_solution_quantity is not None:
        session.add(DrugCoatingUsageLedger(
            site_id=batch.site_id, batch_id=cmd.batch_id, usage_type="ISSUED", quantity=Decimal(cmd.initial_drug_solution_quantity),
            uom=cmd.initial_drug_solution_uom or "g", recorded_by=actor_user_id, occurred_at=datetime.now(timezone.utc),
        ))
        await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="ddcp_process_operation",
        aggregate_id=operation.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="CoatingRunStarted", event_payload={"id": str(operation.id), "batch_id": str(cmd.batch_id)},
        expected_version=None, command_type="StartCoatingRun",
    )


async def _load_operation_for_update(session: AsyncSession, operation_id: uuid.UUID, expected_version: int) -> DdcpProcessOperation:
    result = await session.execute(select(DdcpProcessOperation).where(DdcpProcessOperation.id == operation_id).with_for_update())
    operation = result.scalar_one_or_none()
    if operation is None:
        raise NotFoundError("Coating run not found")
    if operation.version != expected_version:
        raise StaleVersionError("Operation was modified since it was read", expected_version=expected_version, current_version=operation.version)
    return operation


# ---------------------------------------------------------------------------------------------------
# recordCoatingProcessEvidence() — COAT-FR-006/007. Appends to process_parameters, optionally evaluated
# through a released rule (SG-148/150 pattern) to flag COATING_PARAMETER_EXCURSION -- no numeric limit
# is baselined anywhere, so the caller supplies the released rule when they want the excursion check.
# ---------------------------------------------------------------------------------------------------


class RecordCoatingProcessEvidenceCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    parameter_code: str
    value: str
    uom: str | None = None
    acceptance_rule_id: str | None = None


async def record_coating_process_evidence(
    session: AsyncSession, cmd: RecordCoatingProcessEvidenceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state not in ("EXECUTION", "HOLD"):
        raise InvalidTransitionError("Coating process evidence can only be recorded while the run is executing", current_state=operation.state)

    excursion = False
    if cmd.acceptance_rule_id:
        eval_receipt = await rules_commands.evaluate_rule(
            session,
            rules_commands.EvaluateRuleCommand(
                idempotency_key=f"{cmd.idempotency_key}:rule-eval", rule_id=cmd.acceptance_rule_id, inputs={"value": cmd.value},
                aggregate_type="ddcp_process_operation", aggregate_id=operation.id, aggregate_version=operation.version,
            ),
            actor_user_id,
        )
        evaluation = await session.get(RuleEvaluation, eval_receipt.aggregate_id)
        excursion = (evaluation.outcome if evaluation else "ERROR") == "FAIL"

    entry = {
        "parameter_code": cmd.parameter_code, "value": cmd.value, "uom": cmd.uom, "excursion": excursion,
        "actor_user_id": str(actor_user_id), "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    old_state = operation.state
    operation.process_parameters = {"readings": [*(operation.process_parameters or {}).get("readings", []), entry]}
    if excursion:
        operation.requires_deviation = True
        operation.state = "HOLD"
    operation.version += 1

    event_type = "COATING_PARAMETER_EXCURSION" if excursion else "CoatingEvidenceRecorded"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="ddcp_process_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type=event_type, event_payload={"id": str(operation.id), "parameter_code": cmd.parameter_code, "excursion": excursion},
        expected_version=cmd.expected_version, command_type="RecordCoatingProcessEvidence",
    )


# ---------------------------------------------------------------------------------------------------
# recordDrugLoadingResult() — COAT-FR-011/012/014. Rules-engine-evaluated (SG-148/150 pattern), stored
# via device_functional_test_link (test_type=COATING_INTEGRITY by default).
# ---------------------------------------------------------------------------------------------------


class RecordDrugLoadingResultCommand(CommandEnvelope):
    batch_id: uuid.UUID
    unit_or_sample_id: str
    measured_value: str
    uom: str
    acceptance_rule_id: str
    test_type: str = "COATING_INTEGRITY"


async def record_drug_loading_result(
    session: AsyncSession, cmd: RecordDrugLoadingResultCommand, actor_user_id: uuid.UUID
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
            idempotency_key=f"{cmd.idempotency_key}:rule-eval", rule_id=cmd.acceptance_rule_id, inputs={"value": cmd.measured_value},
            aggregate_type="batch", aggregate_id=cmd.batch_id, aggregate_version=None,
        ),
        actor_user_id,
    )
    evaluation = await session.get(RuleEvaluation, eval_receipt.aggregate_id)
    outcome = evaluation.outcome if evaluation else "ERROR"
    result_state = "PASS" if outcome != "FAIL" else "OOS"

    link = DeviceFunctionalTestLink(
        site_id=batch.site_id, batch_id=cmd.batch_id, test_type=cmd.test_type,
        qc_record_reference={"unit_or_sample_id": cmd.unit_or_sample_id, "measured_value": cmd.measured_value, "uom": cmd.uom, "rule_evaluation_id": str(eval_receipt.aggregate_id)},
        result_state=result_state, blocks_release=result_state != "PASS", linked_at=datetime.now(timezone.utc), version=1,
    )
    session.add(link)
    await session.flush()

    event_type = "DRUG_LOADING_OOS" if result_state == "OOS" else "DrugLoadingRecorded"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type=event_type, event_payload={"id": str(link.id), "result_state": result_state},
        expected_version=None, command_type="RecordDrugLoadingResult",
    )


# ---------------------------------------------------------------------------------------------------
# recordDeviceFunctionalTest() — COAT-FR-013/015/016. No dedicated function is named in Document 57's own
# 9-function catalogue for a plain (non-rule-evaluated) device/combined-product functional result --
# recordDrugLoadingResult() is specifically rule-evaluated (SG-148/150 pattern) and would force an
# acceptance_rule_id onto every dimensional/release-elution/coating-integrity-inspection reading even when
# the result is a simple recorded PASS/FAIL/inspection outcome. Derived the same way Document 54's
# DeviceAssemblyRecord commands were derived for an entity with no named writer -- reuses
# device_functional_test_link verbatim, no rule evaluation, no new table.
# ---------------------------------------------------------------------------------------------------


class RecordDeviceFunctionalTestCommand(CommandEnvelope):
    batch_id: uuid.UUID
    test_type: str
    qc_record_reference: dict
    method_reference: dict | None = None
    result_state: str = "PENDING"


async def record_device_functional_test(
    session: AsyncSession, cmd: RecordDeviceFunctionalTestCommand, actor_user_id: uuid.UUID
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
        method_reference=cmd.method_reference, result_state=cmd.result_state, blocks_release=cmd.result_state != "PASS",
        linked_at=datetime.now(timezone.utc), version=1,
    )
    session.add(link)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="CoatedDeviceFunctionalTestRecorded", event_payload={"id": str(link.id), "test_type": link.test_type, "result_state": link.result_state},
        expected_version=None, command_type="RecordDeviceFunctionalTest",
    )


# ---------------------------------------------------------------------------------------------------
# recordCoatedDeviceDisposition() — COAT-FR-025. "Recoating/stripping/reprocessing default prohibited
# unless released validated route explicitly permits and drug/device impact assessed." Same
# default-disallow discipline as PFS-FR-027/INJ-FR-022, reusing ReworkRouteRequiredError verbatim.
# Reuses device_assembly_record (assembly_step=FINAL_DISPOSITION), no new table.
# ---------------------------------------------------------------------------------------------------


class RecordCoatedDeviceDispositionCommand(CommandEnvelope):
    batch_id: uuid.UUID
    unit_identifier: str
    result: str  # PASS | REJECT | REWORK
    reason: str | None = None
    drug_device_impact_assessment: dict | None = None
    rework_procedure_reference: dict | None = None


async def record_coated_device_disposition(
    session: AsyncSession, cmd: RecordCoatedDeviceDispositionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.result not in ("PASS", "REJECT", "REWORK"):
        raise ValidationFailedError("result must be PASS, REJECT or REWORK")
    if cmd.result in ("REJECT", "REWORK") and not cmd.reason:
        raise ValidationFailedError("reason is required for a REJECT or REWORK disposition")
    if cmd.result == "REWORK" and (not cmd.rework_procedure_reference or not cmd.drug_device_impact_assessment):
        raise ReworkRouteRequiredError(
            "Recoating/stripping/reprocessing is disallowed by default (COAT-FR-025) -- an explicit "
            "released-procedure reference and a drug/device impact assessment are both required"
        )

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    record = DeviceAssemblyRecord(
        site_id=batch.site_id, batch_id=cmd.batch_id, unit_identifier=cmd.unit_identifier, assembly_step="FINAL_DISPOSITION",
        component_lot_reference={},
        process_parameters={"reason": cmd.reason, "drug_device_impact_assessment": cmd.drug_device_impact_assessment, "rework_procedure_reference": cmd.rework_procedure_reference},
        performed_by=actor_user_id, result=cmd.result, occurred_at=datetime.now(timezone.utc), version=1,
    )
    session.add(record)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_assembly_record",
        aggregate_id=record.id, version=1, action="Created", actor_user_id=actor_user_id, reason=cmd.reason, old_state=None,
        event_type="CoatedDeviceDispositioned", event_payload={"id": str(record.id), "unit_identifier": cmd.unit_identifier, "result": cmd.result},
        expected_version=None, command_type="RecordCoatedDeviceDisposition",
    )


# ---------------------------------------------------------------------------------------------------
# bindDeviceToCoatingConstituent() — COAT-FR-010. Reuses ddcp_unit_binding (binding_type=
# DEVICE_TO_COATING_CONSTITUENT), the same shared table/duplicate-use discipline Document 55's
# bind_drug_container_to_injector_unit() already established.
# ---------------------------------------------------------------------------------------------------


class BindDeviceToCoatingConstituentCommand(CommandEnvelope):
    batch_id: uuid.UUID
    device_unit_reference: dict
    coating_solution_reference: dict


async def bind_device_to_coating_constituent(
    session: AsyncSession, cmd: BindDeviceToCoatingConstituentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    device_key = cmd.device_unit_reference.get("unit_id") or cmd.device_unit_reference.get("serial")
    existing_bindings = (
        await session.execute(
            select(DdcpUnitBinding).where(DdcpUnitBinding.binding_type == "DEVICE_TO_COATING_CONSTITUENT", DdcpUnitBinding.state == "BOUND")
        )
    ).scalars().all()
    for b in existing_bindings:
        existing_key = b.primary_unit_reference.get("unit_id") or b.primary_unit_reference.get("serial")
        if existing_key == device_key:
            raise DeviceToCoatingBindingAlreadyUsedError("Device unit is already bound to a coating constituent", device_unit_reference=cmd.device_unit_reference, existing_binding_id=str(b.id))

    binding = DdcpUnitBinding(
        site_id=batch.site_id, batch_id=cmd.batch_id, binding_type="DEVICE_TO_COATING_CONSTITUENT",
        primary_unit_reference=cmd.device_unit_reference, bound_constituent_reference=cmd.coating_solution_reference,
        state="BOUND", bound_by=actor_user_id, bound_at=datetime.now(timezone.utc), version=1,
    )
    session.add(binding)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="ddcp_unit_binding",
        aggregate_id=binding.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="CoatedDeviceGenealogyBound", event_payload={"id": str(binding.id)}, expected_version=None,
        command_type="BindDeviceToCoatingConstituent",
    )


# ---------------------------------------------------------------------------------------------------
# completeCoatingRun() — COAT-FR-009/026. Dual reconciliation: device-unit side (production_count_ledger,
# count_type=COATED) and drug/coating-material side (drug_coating_usage_ledger) must each be
# structurally constructible -- no numeric variance tolerance is baselined anywhere (same SG-148/150
# posture as every other complete_*() function in this module family).
# ---------------------------------------------------------------------------------------------------


class CompleteCoatingRunCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    reason: str | None = None


async def complete_coating_run(
    session: AsyncSession, cmd: CompleteCoatingRunCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state != "EXECUTION":
        if operation.state == "HOLD":
            raise CoatingReconciliationFailedError("Coating run has an unresolved hold (parameter excursion)")
        raise InvalidTransitionError("Only an executing coating run can be completed", current_state=operation.state)

    coated_count = (
        await session.execute(
            select(func.coalesce(func.sum(ProductionCountLedger.quantity), 0)).where(
                ProductionCountLedger.batch_id == operation.batch_id, ProductionCountLedger.count_type == "COATED",
            )
        )
    ).scalar()
    if not coated_count:
        raise CoatingReconciliationFailedError("No COATED units recorded for this batch -- device-unit reconciliation is not constructible")

    issued = (
        await session.execute(
            select(func.coalesce(func.sum(DrugCoatingUsageLedger.quantity), 0)).where(
                DrugCoatingUsageLedger.batch_id == operation.batch_id, DrugCoatingUsageLedger.usage_type == "ISSUED",
            )
        )
    ).scalar()
    if not issued:
        raise CoatingReconciliationFailedError("No ISSUED drug/coating usage recorded for this batch -- material reconciliation is not constructible")

    old_state = operation.state
    operation.state = "COMPLETE"
    operation.ended_at = datetime.now(timezone.utc)
    operation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="ddcp_process_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id, reason=cmd.reason,
        old_state=old_state, event_type="CoatingRunCompleted", event_payload={"id": str(operation.id), "state": operation.state},
        expected_version=cmd.expected_version, command_type="CompleteCoatingRun",
    )


# ---------------------------------------------------------------------------------------------------
# recordPostSterilizationTest() — COAT-FR-018/019/020. Reuses device_functional_test_link, carrying the
# sterilization reference inside qc_record_reference (never a duplicated sterilization-cycle table --
# Document 42 owns that data, referenced only, same discipline every other DDCP document already uses).
# ---------------------------------------------------------------------------------------------------


class RecordPostSterilizationTestCommand(CommandEnvelope):
    batch_id: uuid.UUID
    sterilization_reference: dict
    test_type: str
    qc_record_reference: dict = {}
    result_state: str = "PENDING"


async def record_post_sterilization_test(
    session: AsyncSession, cmd: RecordPostSterilizationTestCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    link = DeviceFunctionalTestLink(
        site_id=batch.site_id, batch_id=cmd.batch_id, test_type=cmd.test_type,
        qc_record_reference={**cmd.qc_record_reference, "sterilization_reference": cmd.sterilization_reference},
        result_state=cmd.result_state, blocks_release=cmd.result_state != "PASS", linked_at=datetime.now(timezone.utc), version=1,
    )
    session.add(link)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="PostSterilizationTestRecorded", event_payload={"id": str(link.id), "test_type": link.test_type, "result_state": link.result_state},
        expected_version=None, command_type="RecordPostSterilizationTest",
    )


# ---------------------------------------------------------------------------------------------------
# evaluateCoatedDeviceReleaseReadiness() — COAT-FR-027/028. Same three-checkpoint composition pattern.
# ---------------------------------------------------------------------------------------------------


async def evaluate_coated_device_release_readiness(session: AsyncSession, batch_id: uuid.UUID, actor_user_id: uuid.UUID) -> dict:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    drug_ok = any(h.from_constituent in ("DRUG", "BIOLOGIC") and h.state == "ACCEPTED" for h in handoffs)
    substrate_handoffs_pending = [h for h in handoffs if h.from_constituent == "DEVICE" and h.state != "ACCEPTED"]

    test_links = (
        await session.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch_id).order_by(DeviceFunctionalTestLink.linked_at))
    ).scalars().all()
    latest_by_test_type: dict[str, DeviceFunctionalTestLink] = {}
    for link in test_links:
        latest_by_test_type[link.test_type] = link
    failed_tests = [t for t in latest_by_test_type.values() if t.blocks_release and t.result_state not in ("PASS",)]

    operations = (await session.execute(select(DdcpProcessOperation).where(DdcpProcessOperation.batch_id == batch_id, DdcpProcessOperation.operation_type == "COATING_RUN"))).scalars().all()
    open_holds = [o for o in operations if o.requires_deviation]

    checkpoint_results: dict[str, dict] = {}
    checkpoint_results["DRUG_CONSTITUENT"] = (
        {"state": "SATISFIED", "blockers": []} if drug_ok
        else {"state": "BLOCKED", "blockers": [{"code": "COATING_DRUG_NOT_RELEASED", "message": "No accepted coating drug/solution handoff"}]}
    )
    device_blockers = []
    if substrate_handoffs_pending:
        device_blockers.append({"code": "SUBSTRATE_NOT_RELEASED", "message": f"{len(substrate_handoffs_pending)} substrate handoff(s) not accepted"})
    for test in failed_tests:
        device_blockers.append({"code": "DRUG_LOADING_OOS" if test.result_state == "OOS" else "COATED_DEVICE_TEST_FAILED", "message": f"{test.test_type} result is {test.result_state}", "test_link_id": str(test.id)})
    checkpoint_results["DEVICE_CONSTITUENT"] = {"state": "SATISFIED", "blockers": []} if not device_blockers else {"state": "BLOCKED", "blockers": device_blockers}

    combined_blockers = list(checkpoint_results["DRUG_CONSTITUENT"]["blockers"]) + list(checkpoint_results["DEVICE_CONSTITUENT"]["blockers"])
    if open_holds:
        combined_blockers.append({"code": "COATING_RECONCILIATION_FAILED", "message": f"{len(open_holds)} coating run(s) have an unresolved hold"})
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


class CreateCoatedDeviceBatchEvidencePackageCommand(CommandEnvelope):
    batch_id: uuid.UUID


async def create_coated_device_batch_evidence_package(
    session: AsyncSession, cmd: CreateCoatedDeviceBatchEvidencePackageCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (await session.execute(select(ConstituentHandoff.id, ConstituentHandoff.version).where(ConstituentHandoff.batch_id == cmd.batch_id))).all()
    operations = (await session.execute(select(DdcpProcessOperation.id, DdcpProcessOperation.version).where(DdcpProcessOperation.batch_id == cmd.batch_id))).all()
    bindings = (await session.execute(select(DdcpUnitBinding.id, DdcpUnitBinding.version).where(DdcpUnitBinding.batch_id == cmd.batch_id))).all()
    test_links = (await session.execute(select(DeviceFunctionalTestLink.id, DeviceFunctionalTestLink.version).where(DeviceFunctionalTestLink.batch_id == cmd.batch_id))).all()
    checkpoints = (await session.execute(select(DdcpReleaseCheckpoint.id, DdcpReleaseCheckpoint.version).where(DdcpReleaseCheckpoint.batch_id == cmd.batch_id))).all()

    evidence_set = {
        "constituent_handoffs": [{"id": str(i), "version": v} for i, v in handoffs],
        "ddcp_process_operations": [{"id": str(i), "version": v} for i, v in operations],
        "ddcp_unit_bindings": [{"id": str(i), "version": v} for i, v in bindings],
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
        event_type="CoatedDeviceBatchPackageGenerated", event_payload={"id": str(manifest.id), "manifest_version": manifest.manifest_version, "digest": digest},
        expected_version=None, command_type="CreateCoatedDeviceBatchEvidencePackage",
    )


# ---------------------------------------------------------------------------------------------------
# traceCoatedDeviceComplaint() — COAT-FR-019/030. Pure read genealogy composition by batch_id, including
# ddcp_unit_binding (substrate<->coating constituent) and drug_coating_usage_ledger.
# ---------------------------------------------------------------------------------------------------


async def trace_coated_device_complaint(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    bindings = (await session.execute(select(DdcpUnitBinding).where(DdcpUnitBinding.batch_id == batch_id))).scalars().all()
    test_links = (await session.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch_id))).scalars().all()
    usage = (await session.execute(select(DrugCoatingUsageLedger).where(DrugCoatingUsageLedger.batch_id == batch_id))).scalars().all()

    return {
        "batch_id": str(batch_id),
        "substrate_and_drug_handoffs": [
            {"id": str(h.id), "from_constituent": h.from_constituent, "to_constituent": h.to_constituent, "source_batch_reference": h.source_batch_reference, "state": h.state}
            for h in handoffs
        ],
        "device_to_coating_bindings": [
            {"id": str(b.id), "primary_unit_reference": b.primary_unit_reference, "bound_constituent_reference": b.bound_constituent_reference} for b in bindings
        ],
        "functional_test_links": [{"id": str(t.id), "test_type": t.test_type, "result_state": t.result_state} for t in test_links],
        "drug_coating_usage": [{"id": str(u.id), "usage_type": u.usage_type, "quantity": str(u.quantity), "uom": u.uom} for u in usage],
    }
