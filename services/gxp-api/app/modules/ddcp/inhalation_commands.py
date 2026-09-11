"""Document 56 (SPEC-DDCP-003, INH-FR-001..030) — Inhalation MDI/DPI DDCP Manufacturing Profile.

SG-150: no Document 112 schema exists for this document. Reuses Document 54's tables/functions verbatim
per the DDCP Platform Rule, the same reuse strategy `injector_commands.py` (Document 55) already applies:
`ddcp_profile_version`/`constituent_requirement` (own subtype vocabulary `INHALATION_SUBTYPES`),
`constituent_handoff`, `device_assembly_record` (valve/crimp/actuator steps), `device_functional_test_link`
(closure/leak/dose/aerodynamic test types), `production_count_ledger`, `ddcp_release_checkpoint`,
`batch_evidence_manifest`. `ddcp_process_operation` (operation_type=INHALER_FILL) is the one shared-but-new
table this document needs (Document 55 already introduced it) -- no additional new tables for this
document beyond what Document 55 already added.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.batch_execution.models import Batch
from app.modules.ddcp.commands import _assert_product_version_for_profile, _receipt_from_existing, _write_receipt
from app.modules.ddcp.models import (
    INHALATION_SUBTYPES,
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
    ProductionCountLedger,
)
from app.modules.equipment.models import EquipmentAsset
from app.modules.rules import commands as rules_commands
from app.modules.rules.models import RuleEvaluation
from app.mutation.errors import (
    BlendHoldTimeExceededError,
    DoseUnitBindingAlreadyUsedError,
    FillRouteMismatchError,
    InhalationProfileNotEffectiveError,
    InhalerReconciliationFailedError,
    InvalidTransitionError,
    NotFoundError,
    ProfileSchemaInvalidError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

# ---------------------------------------------------------------------------------------------------
# DdcpProfileVersion — INH-FR-001/002/003/004/005. createInhalationProfileVersion().
# release_injectable_profile_version() from commands.py is reused verbatim.
# ---------------------------------------------------------------------------------------------------


class CreateInhalationProfileVersionCommand(CommandEnvelope):
    site_id: uuid.UUID
    profile_code: str
    product_version_id: uuid.UUID  # SG-175 -- must be a RELEASED product with manufacturing_profile_code="inhalation_ddcp"
    subtype: str  # MDI | DPI
    fill_route: str | None = None
    environment_profile_id: str | None = None
    constituent_architecture: dict = {}
    required_controls: dict = {}
    release_checkpoint_set: dict = {"checkpoints": list(RELEASE_CHECKPOINT_CODES)}
    constituent_requirements: list[dict] = []


async def create_inhalation_profile_version(
    session: AsyncSession, cmd: CreateInhalationProfileVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.subtype not in INHALATION_SUBTYPES:
        raise ProfileSchemaInvalidError("Unrecognized subtype", allowed=list(INHALATION_SUBTYPES))
    for req in cmd.constituent_requirements:
        if not req.get("component_role"):
            raise ProfileSchemaInvalidError("Every constituent_requirement needs a component_role")
    await _assert_product_version_for_profile(
        session, product_version_id=cmd.product_version_id, site_id=cmd.site_id,
        expected_manufacturing_profile_code="inhalation_ddcp",
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
        subtype=cmd.subtype, version=next_version + 1,
        state="DRAFT",
        constituent_architecture={"fillRoute": cmd.fill_route, "environmentProfileId": cmd.environment_profile_id, **cmd.constituent_architecture},
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
        old_state=None, event_type="InhalationProfileDraftCreated",
        event_payload={"id": str(profile.id), "profile_code": profile.profile_code, "version": profile.version},
        expected_version=None, command_type="CreateInhalationProfileVersion",
    )


# ---------------------------------------------------------------------------------------------------
# evaluateInhalationReadiness() — INH-FR-002/003/004/005/018. Pure read; environment readiness (INH-FR-
# 018) is a caller-supplied status snapshot -- Document 56 §7 itself says these limits are "product/
# validation-controlled, not generic constants", so no humidity/temperature threshold is baked in here.
# ---------------------------------------------------------------------------------------------------


async def evaluate_inhalation_readiness(
    session: AsyncSession, *, batch_id: uuid.UUID, profile_version_id: uuid.UUID, environment_status: dict | None = None,
) -> dict:
    profile = await session.get(DdcpProfileVersion, profile_version_id)
    if profile is None or profile.state != "RELEASED":
        raise InhalationProfileNotEffectiveError("Inhalation profile version is not RELEASED / effective", profile_version_id=str(profile_version_id))

    requirements = (
        await session.execute(select(ConstituentRequirement).where(ConstituentRequirement.ddcp_profile_version_id == profile_version_id, ConstituentRequirement.mandatory == True))  # noqa: E712
    ).scalars().all()
    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    accepted_roles = {h.to_constituent for h in handoffs if h.state == "ACCEPTED"}

    blockers = []
    for req in requirements:
        if req.component_role not in accepted_roles:
            code = "FORMULATION_NOT_RELEASED" if req.constituent_type in ("DRUG", "BIOLOGIC") else "INHALER_COMPONENT_NOT_RELEASED"
            blockers.append({"code": code, "message": f"No accepted handoff for required component_role '{req.component_role}'", "component_role": req.component_role})

    environment_required = bool((profile.required_controls or {}).get("environmentProfileId") or profile.constituent_architecture.get("environmentProfileId"))
    if environment_required and environment_status is not None and environment_status.get("ready") is False:
        blockers.append({"code": "ENVIRONMENT_NOT_READY", "message": "Environment status snapshot reports not ready", "environment_status": environment_status})

    return {"batch_id": str(batch_id), "profile_version_id": str(profile_version_id), "ready": not blockers, "blockers": blockers}


# ---------------------------------------------------------------------------------------------------
# startInhalerFillRun() — INH-FR-007/008/019/020. Reuses DdcpProcessOperation (operation_type=
# INHALER_FILL). INH-FR-019 (blend/fill hold time) reuses the exact SG-148/150 rules-engine pattern
# already established for PFS-FR-007/Document 54.
# ---------------------------------------------------------------------------------------------------


class StartInhalerFillRunCommand(CommandEnvelope):
    batch_id: uuid.UUID
    profile_version_id: uuid.UUID
    fill_route: str
    line_id: uuid.UUID | None = None
    equipment_id: uuid.UUID | None = None
    program_id: str | None = None
    program_version: str | None = None
    environment_status: dict | None = None
    blend_hold_limit_rule_id: str | None = None


async def start_inhaler_fill_run(
    session: AsyncSession, cmd: StartInhalerFillRunCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    readiness = await evaluate_inhalation_readiness(session, batch_id=cmd.batch_id, profile_version_id=cmd.profile_version_id, environment_status=cmd.environment_status)
    if not readiness["ready"]:
        raise ValidationFailedError("Inhalation readiness is not satisfied", blockers=readiness["blockers"])

    profile = await session.get(DdcpProfileVersion, cmd.profile_version_id)
    declared_route = profile.constituent_architecture.get("fillRoute") if profile else None
    if declared_route and declared_route != cmd.fill_route:
        raise FillRouteMismatchError("fill_route does not match the profile's declared fillRoute", declared_route=declared_route, provided_route=cmd.fill_route)

    if cmd.equipment_id is not None and await session.get(EquipmentAsset, cmd.equipment_id) is None:
        raise NotFoundError("Referenced equipment asset not found")

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    fill_start_time = datetime.now(timezone.utc)

    if cmd.blend_hold_limit_rule_id:
        formulation_handoff = (
            await session.execute(
                select(ConstituentHandoff)
                .where(ConstituentHandoff.batch_id == cmd.batch_id, ConstituentHandoff.from_constituent.in_(("DRUG", "BIOLOGIC")), ConstituentHandoff.state == "ACCEPTED")
                .order_by(ConstituentHandoff.accepted_at.desc())
            )
        ).scalars().first()
        if formulation_handoff is not None and formulation_handoff.accepted_at is not None:
            elapsed_hours = Decimal((fill_start_time - formulation_handoff.accepted_at).total_seconds()) / Decimal(3600)
            eval_receipt = await rules_commands.evaluate_rule(
                session,
                rules_commands.EvaluateRuleCommand(
                    idempotency_key=f"{cmd.idempotency_key}:hold-time-eval", rule_id=cmd.blend_hold_limit_rule_id,
                    inputs={"elapsed_hours": str(elapsed_hours)}, aggregate_type="constituent_handoff",
                    aggregate_id=formulation_handoff.id, aggregate_version=formulation_handoff.version,
                ),
                actor_user_id,
            )
            hold_evaluation = await session.get(RuleEvaluation, eval_receipt.aggregate_id)
            if hold_evaluation is not None and hold_evaluation.outcome == "FAIL":
                raise BlendHoldTimeExceededError(
                    "Formulation/blend-to-filling hold time exceeds the released limit",
                    elapsed_hours=str(elapsed_hours), handoff_id=str(formulation_handoff.id), rule_evaluation_id=str(eval_receipt.aggregate_id),
                )

    active = (
        await session.execute(
            select(DdcpProcessOperation).where(
                DdcpProcessOperation.batch_id == cmd.batch_id, DdcpProcessOperation.operation_type == "INHALER_FILL",
                DdcpProcessOperation.state.in_(("SETUP", "EXECUTION", "HOLD")),
            )
        )
    ).scalar_one_or_none()
    if active is not None:
        raise InvalidTransitionError("Batch already has an active inhaler fill run", existing_operation_id=str(active.id))

    operation = DdcpProcessOperation(
        site_id=batch.site_id, batch_id=cmd.batch_id, operation_type="INHALER_FILL", line_id=cmd.line_id,
        equipment_id=cmd.equipment_id, program_id=cmd.program_id, program_version=cmd.program_version,
        process_parameters={"fill_route": cmd.fill_route}, environment_reference=cmd.environment_status,
        readiness_reference=readiness, started_at=fill_start_time, state="EXECUTION", version=1,
    )
    session.add(operation)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="ddcp_process_operation",
        aggregate_id=operation.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="InhalerFillStarted", event_payload={"id": str(operation.id), "batch_id": str(cmd.batch_id), "fill_route": cmd.fill_route},
        expected_version=None, command_type="StartInhalerFillRun",
    )


async def _load_operation_for_update(session: AsyncSession, operation_id: uuid.UUID, expected_version: int) -> DdcpProcessOperation:
    result = await session.execute(select(DdcpProcessOperation).where(DdcpProcessOperation.id == operation_id).with_for_update())
    operation = result.scalar_one_or_none()
    if operation is None:
        raise NotFoundError("Inhaler fill run not found")
    if operation.version != expected_version:
        raise StaleVersionError("Operation was modified since it was read", expected_version=expected_version, current_version=operation.version)
    return operation


# ---------------------------------------------------------------------------------------------------
# recordCrimpOrClosureResult() — INH-FR-009/012. Rules-engine-evaluated (SG-148/150 pattern) closure/
# crimp/leak result, stored via device_functional_test_link (test_type=SEAL, reused verbatim).
# ---------------------------------------------------------------------------------------------------


class RecordCrimpOrClosureResultCommand(CommandEnvelope):
    batch_id: uuid.UUID
    unit_or_sample_id: str
    measured_value: str
    uom: str
    acceptance_rule_id: str
    test_type: str = "SEAL"


async def record_crimp_or_closure_result(
    session: AsyncSession, cmd: RecordCrimpOrClosureResultCommand, actor_user_id: uuid.UUID
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
    result_state = "PASS" if outcome != "FAIL" else "FAIL"

    link = DeviceFunctionalTestLink(
        site_id=batch.site_id, batch_id=cmd.batch_id, test_type=cmd.test_type,
        qc_record_reference={"unit_or_sample_id": cmd.unit_or_sample_id, "measured_value": cmd.measured_value, "uom": cmd.uom, "rule_evaluation_id": str(eval_receipt.aggregate_id)},
        result_state=result_state, blocks_release=result_state != "PASS", linked_at=datetime.now(timezone.utc), version=1,
    )
    session.add(link)
    await session.flush()

    event_type = "CLOSURE_TEST_FAILED" if result_state == "FAIL" else "InhalerClosureRecorded"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type=event_type, event_payload={"id": str(link.id), "result_state": result_state},
        expected_version=None, command_type="RecordCrimpOrClosureResult",
    )


# ---------------------------------------------------------------------------------------------------
# recordInhalerDoseTest() / recordDoseCounterTest() — INH-FR-013/014/015/016/017. Both reuse
# device_functional_test_link verbatim (test_type unenforced documented set).
# ---------------------------------------------------------------------------------------------------


class RecordInhalerDoseTestCommand(CommandEnvelope):
    batch_id: uuid.UUID
    test_type: str  # DELIVERED_DOSE | AERODYNAMIC_PARTICLE_SIZE | SPRAY_PATTERN | PRIMING | ...
    qc_record_reference: dict
    method_reference: dict | None = None
    result_state: str = "PENDING"


async def record_inhaler_dose_test(
    session: AsyncSession, cmd: RecordInhalerDoseTestCommand, actor_user_id: uuid.UUID
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

    event_type = "INHALER_QC_OOS" if cmd.result_state == "OOS" else "InhalerDoseTestRecorded"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type=event_type, event_payload={"id": str(link.id), "test_type": link.test_type, "result_state": link.result_state},
        expected_version=None, command_type="RecordInhalerDoseTest",
    )


class RecordDoseCounterTestCommand(CommandEnvelope):
    batch_id: uuid.UUID
    unit_or_sample_id: str
    program_version: str | None = None
    result_state: str = "PENDING"


async def record_dose_counter_test(
    session: AsyncSession, cmd: RecordDoseCounterTestCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    link = DeviceFunctionalTestLink(
        site_id=batch.site_id, batch_id=cmd.batch_id, test_type="DOSE_COUNTER",
        qc_record_reference={"unit_or_sample_id": cmd.unit_or_sample_id, "program_version": cmd.program_version},
        result_state=cmd.result_state, blocks_release=cmd.result_state != "PASS", linked_at=datetime.now(timezone.utc), version=1,
    )
    session.add(link)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="DoseCounterTestRecorded", event_payload={"id": str(link.id), "result_state": link.result_state},
        expected_version=None, command_type="RecordDoseCounterTest",
    )


# ---------------------------------------------------------------------------------------------------
# completeInhalerManufacturingRun() — INH-FR-020/021/022/026. Structural completeness only, same
# SG-148/150 posture as Document 54/55's own complete_*() functions.
# ---------------------------------------------------------------------------------------------------


class CompleteInhalerManufacturingRunCommand(CommandEnvelope):
    operation_id: uuid.UUID
    expected_version: int
    reason: str | None = None


async def complete_inhaler_manufacturing_run(
    session: AsyncSession, cmd: CompleteInhalerManufacturingRunCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    operation = await _load_operation_for_update(session, cmd.operation_id, cmd.expected_version)
    if operation.state != "EXECUTION":
        if operation.state == "HOLD":
            raise InhalerReconciliationFailedError("Inhaler fill run has an unresolved hold")
        raise InvalidTransitionError("Only an executing inhaler fill run can be completed", current_state=operation.state)

    filled_count = (
        await session.execute(
            select(func.coalesce(func.sum(ProductionCountLedger.quantity), 0)).where(
                ProductionCountLedger.batch_id == operation.batch_id, ProductionCountLedger.count_type == "FILLED",
            )
        )
    ).scalar()
    if not filled_count:
        raise InhalerReconciliationFailedError("No FILLED units recorded for this batch -- reconciliation is not constructible")

    old_state = operation.state
    operation.state = "COMPLETE"
    operation.ended_at = datetime.now(timezone.utc)
    operation.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=operation.site_id, aggregate_type="ddcp_process_operation",
        aggregate_id=operation.id, version=operation.version, action="Changed", actor_user_id=actor_user_id, reason=cmd.reason,
        old_state=old_state, event_type="InhalerManufacturingCompleted", event_payload={"id": str(operation.id), "state": operation.state},
        expected_version=cmd.expected_version, command_type="CompleteInhalerManufacturingRun",
    )


# ---------------------------------------------------------------------------------------------------
# evaluateInhalerReleaseReadiness() — INH-FR-025/026/027. Same three-checkpoint composition pattern.
# ---------------------------------------------------------------------------------------------------


async def evaluate_inhaler_release_readiness(session: AsyncSession, batch_id: uuid.UUID, actor_user_id: uuid.UUID) -> dict:
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
    failed_tests = [t for t in latest_by_test_type.values() if t.blocks_release and t.result_state not in ("PASS",)]

    operations = (await session.execute(select(DdcpProcessOperation).where(DdcpProcessOperation.batch_id == batch_id, DdcpProcessOperation.operation_type == "INHALER_FILL"))).scalars().all()
    open_holds = [o for o in operations if o.requires_deviation]

    checkpoint_results: dict[str, dict] = {}
    checkpoint_results["DRUG_CONSTITUENT"] = (
        {"state": "SATISFIED", "blockers": []} if drug_ok
        else {"state": "BLOCKED", "blockers": [{"code": "FORMULATION_NOT_RELEASED", "message": "No accepted formulation/drug handoff"}]}
    )
    device_blockers = []
    if device_handoffs_pending:
        device_blockers.append({"code": "INHALER_COMPONENT_NOT_RELEASED", "message": f"{len(device_handoffs_pending)} device handoff(s) not accepted"})
    for test in failed_tests:
        device_blockers.append({"code": "INHALER_QC_OOS" if test.result_state == "OOS" else "CLOSURE_TEST_FAILED", "message": f"{test.test_type} result is {test.result_state}", "test_link_id": str(test.id)})
    checkpoint_results["DEVICE_CONSTITUENT"] = {"state": "SATISFIED", "blockers": []} if not device_blockers else {"state": "BLOCKED", "blockers": device_blockers}

    combined_blockers = list(checkpoint_results["DRUG_CONSTITUENT"]["blockers"]) + list(checkpoint_results["DEVICE_CONSTITUENT"]["blockers"])
    if open_holds:
        combined_blockers.append({"code": "INHALER_RECONCILIATION_FAILED", "message": f"{len(open_holds)} fill run(s) have an unresolved hold"})
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


class CreateInhalerBatchEvidencePackageCommand(CommandEnvelope):
    batch_id: uuid.UUID


async def create_inhaler_batch_evidence_package(
    session: AsyncSession, cmd: CreateInhalerBatchEvidencePackageCommand, actor_user_id: uuid.UUID
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
    assembly = (await session.execute(select(DeviceAssemblyRecord.id, DeviceAssemblyRecord.version).where(DeviceAssemblyRecord.batch_id == cmd.batch_id))).all()
    test_links = (await session.execute(select(DeviceFunctionalTestLink.id, DeviceFunctionalTestLink.version).where(DeviceFunctionalTestLink.batch_id == cmd.batch_id))).all()
    checkpoints = (await session.execute(select(DdcpReleaseCheckpoint.id, DdcpReleaseCheckpoint.version).where(DdcpReleaseCheckpoint.batch_id == cmd.batch_id))).all()

    evidence_set = {
        "constituent_handoffs": [{"id": str(i), "version": v} for i, v in handoffs],
        "ddcp_process_operations": [{"id": str(i), "version": v} for i, v in operations],
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
        event_type="InhalerBatchPackageGenerated", event_payload={"id": str(manifest.id), "manifest_version": manifest.manifest_version, "digest": digest},
        expected_version=None, command_type="CreateInhalerBatchEvidencePackage",
    )


# ---------------------------------------------------------------------------------------------------
# traceInhalerLot() — INH-FR-024/030. Pure read genealogy composition by batch_id.
# ---------------------------------------------------------------------------------------------------


async def trace_inhaler_lot(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    assembly = (await session.execute(select(DeviceAssemblyRecord).where(DeviceAssemblyRecord.batch_id == batch_id))).scalars().all()
    test_links = (await session.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch_id))).scalars().all()
    counts = (await session.execute(select(ProductionCountLedger).where(ProductionCountLedger.batch_id == batch_id))).scalars().all()

    return {
        "batch_id": str(batch_id),
        "formulation_and_component_handoffs": [
            {"id": str(h.id), "from_constituent": h.from_constituent, "to_constituent": h.to_constituent, "source_batch_reference": h.source_batch_reference, "state": h.state}
            for h in handoffs
        ],
        "device_assembly_records": [{"id": str(a.id), "assembly_step": a.assembly_step, "result": a.result} for a in assembly],
        "functional_test_links": [{"id": str(t.id), "test_type": t.test_type, "result_state": t.result_state} for t in test_links],
        "production_counts": [{"id": str(c.id), "count_type": c.count_type, "quantity": c.quantity} for c in counts],
    }


# ---------------------------------------------------------------------------------------------------
# bindDoseUnitToDevice() — INH-FR-011. "Track powder dose/blister/capsule lot and device association
# according to unit/lot architecture" (DPI). Reuses ddcp_unit_binding (binding_type=DOSE_UNIT_TO_DEVICE),
# the same shared table/duplicate-use discipline Document 55's drug-container binding and Document 57's
# device-to-coating binding already established (SG-150).
# ---------------------------------------------------------------------------------------------------


class BindDoseUnitToDeviceCommand(CommandEnvelope):
    batch_id: uuid.UUID
    dose_unit_reference: dict  # {"blister_id": ...} or {"capsule_id": ...} or {"reservoir_lot_id": ...}
    device_reference: dict


async def bind_dose_unit_to_device(
    session: AsyncSession, cmd: BindDoseUnitToDeviceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    dose_unit_key = cmd.dose_unit_reference.get("blister_id") or cmd.dose_unit_reference.get("capsule_id") or cmd.dose_unit_reference.get("reservoir_lot_id")
    existing_bindings = (
        await session.execute(
            select(DdcpUnitBinding).where(DdcpUnitBinding.binding_type == "DOSE_UNIT_TO_DEVICE", DdcpUnitBinding.state == "BOUND")
        )
    ).scalars().all()
    for b in existing_bindings:
        existing_key = b.primary_unit_reference.get("blister_id") or b.primary_unit_reference.get("capsule_id") or b.primary_unit_reference.get("reservoir_lot_id")
        if existing_key == dose_unit_key:
            raise DoseUnitBindingAlreadyUsedError("Dose unit is already bound to another device", dose_unit_reference=cmd.dose_unit_reference, existing_binding_id=str(b.id))

    binding = DdcpUnitBinding(
        site_id=batch.site_id, batch_id=cmd.batch_id, binding_type="DOSE_UNIT_TO_DEVICE",
        primary_unit_reference=cmd.dose_unit_reference, bound_constituent_reference=cmd.device_reference,
        state="BOUND", bound_by=actor_user_id, bound_at=datetime.now(timezone.utc), version=1,
    )
    session.add(binding)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="ddcp_unit_binding",
        aggregate_id=binding.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="DoseUnitBoundToDevice", event_payload={"id": str(binding.id)}, expected_version=None,
        command_type="BindDoseUnitToDevice",
    )
