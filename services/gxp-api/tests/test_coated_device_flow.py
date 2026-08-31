"""WP-08 (Document 57, SPEC-DDCP-004, COAT-FR-001..030): Drug-Eluting / Drug-Coated Device DDCP
Manufacturing Profile. SG-150: no Document 112 schema exists for this document -- it reuses Document
54/55's tables/functions plus two shared/new tables: `ddcp_unit_binding` (binding_type=
DEVICE_TO_COATING_CONSTITUENT, shared with Document 55) and `drug_coating_usage_ledger` (new, decimal
mass-balance ledger for COAT-FR-009's dual reconciliation).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.modules.batch.models import Batch
from app.modules.ddcp import coated_device_commands
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp.models import DdcpProcessOperation, DdcpProfileVersion, DdcpUnitBinding, DeviceAssemblyRecord, DeviceFunctionalTestLink
from app.modules.equipment.models import EquipmentAsset
from app.modules.material.models import Material, MaterialLot
from app.modules.product.models import Product
from app.modules.qms import change_commands
from app.modules.recipe.models import Recipe
from app.modules.rules import commands as rules_commands
from app.modules.signature.models import SignaturePolicy
from app.mutation.errors import (
    CoatedDeviceProfileNotEffectiveError,
    CoatingReconciliationFailedError,
    DeviceToCoatingBindingAlreadyUsedError,
    ReworkRouteRequiredError,
    ValidationFailedError,
)
from tests.conftest import idem

PARAM_RULE_ID = "coating-parameter-tolerance"
PARAM_RULE_AST = {
    "op": "and",
    "args": [
        {"op": "gte", "args": [{"var": "value"}, "20"]},
        {"op": "lte", "args": [{"var": "value"}, "30"]},
    ],
}

LOADING_RULE_ID = "coating-drug-loading-tolerance"
LOADING_RULE_AST = {
    "op": "and",
    "args": [
        {"op": "gte", "args": [{"var": "value"}, "0.90"]},
        {"op": "lte", "args": [{"var": "value"}, "1.10"]},
    ],
}


async def _release_rule(db, actor_id, *, rule_id, expression_ast, seed_policy=True):
    if seed_policy:
        db.add(SignaturePolicy(record_type="rule", action="release", meaning="Released", signature_required=False))
        await db.flush()
    draft = await rules_commands.create_draft(
        db,
        rules_commands.CreateRuleDraftCommand(
            idempotency_key=idem(), rule_id=rule_id, rule_type="acceptance", semantic_version="1.0.0",
            expression_ast=expression_ast, input_contract={"value": {"type": "decimal"}}, output_contract={"eligible": {"type": "boolean"}},
            unit_policy={}, precision_policy={"calculation_class": "CC-5", "reported_decimal_places": 2},
            rounding_policy={"policy_version": "DOCUMENT-110-v1.0"},
        ),
        actor_id,
    )
    await rules_commands.validate_rule(db, rules_commands.ValidateRuleCommand(idempotency_key=idem(), rule_object_id=draft.aggregate_id), actor_id)
    await rules_commands.release_rule(db, rules_commands.ReleaseRuleCommand(idempotency_key=idem(), rule_object_id=draft.aggregate_id), actor_id)


async def _create_batch(db, seeded, *, batch_number: str) -> Batch:
    site_id = seeded["site_id"]
    product = Product(site_id=site_id, code=f"PROD-{batch_number}", name="Test Coated Device Product", status="active", version=1)
    db.add(product)
    await db.flush()
    recipe = Recipe(product_id=product.id, version=1, status="active")
    db.add(recipe)
    await db.flush()
    batch = Batch(
        site_id=site_id, product_id=product.id, recipe_id=recipe.id, recipe_version=1, batch_number=batch_number,
        status="in_execution", target_quantity=Decimal("1000"), uom="EA", version=1,
    )
    db.add(batch)
    await db.flush()
    return batch


async def _create_material_lot(db, seeded, *, code: str, actor_id) -> MaterialLot:
    material = Material(site_id=seeded["site_id"], code=code, name=f"Component {code}", uom="EA", version=1)
    db.add(material)
    await db.flush()
    lot = MaterialLot(
        material_id=material.id, site_id=seeded["site_id"], internal_lot=f"LOT-{code}", received_quantity=Decimal("100"),
        available_quantity=Decimal("100"), uom="EA", status="released", received_by_user_id=actor_id,
    )
    db.add(lot)
    await db.flush()
    return lot


async def _create_and_release_profile(db, seeded, actor_id, *, profile_code: str) -> DdcpProfileVersion:
    receipt = await coated_device_commands.create_coated_device_profile_version(
        db,
        coated_device_commands.CreateCoatedDeviceProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], profile_code=profile_code,
            constituent_requirements=[
                {"constituent_type": "DEVICE", "component_role": "substrate", "required_state": "RELEASED"},
                {"constituent_type": "DRUG", "component_role": "coating_solution", "required_state": "RELEASED"},
            ],
        ),
        actor_id,
    )
    profile_id = receipt.aggregate_id
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=profile_id, expected_version=1), actor_id,
    )
    return await db.get(DdcpProfileVersion, profile_id)


async def _accept_constituents(db, seeded, actor_id, batch, substrate_lot, coating_drug_batch):
    for from_c, to_c, ref in (("DEVICE", "substrate", {"lot_id": str(substrate_lot.id)}), ("DRUG", "coating_solution", {"batch_id": str(coating_drug_batch.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )


async def test_create_profile_and_release_has_no_subtype_enum(seeded, db):
    actor_id = seeded["users"]["ddcp.engineer"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="COAT-001")
    assert profile.state == "RELEASED"
    assert profile.subtype is None


async def test_coating_readiness_and_start_run_records_initial_usage(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="COAT-READY")
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-READY-1")

    readiness = await coated_device_commands.evaluate_coating_run_readiness(db, batch_id=batch.id, profile_version_id=profile.id)
    assert readiness["ready"] is False

    substrate_lot = await _create_material_lot(db, seeded, code="SUBSTRATE-1", actor_id=actor_id)
    coating_drug_batch = await _create_batch(db, seeded, batch_number="BULK-COATING-DRUG-1")
    coating_drug_batch.status = "released"
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, substrate_lot, coating_drug_batch)

    readiness = await coated_device_commands.evaluate_coating_run_readiness(db, batch_id=batch.id, profile_version_id=profile.id)
    assert readiness["ready"] is True

    run_receipt = await coated_device_commands.start_coating_run(
        db,
        coated_device_commands.StartCoatingRunCommand(
            idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id,
            initial_drug_solution_quantity="500.0", initial_drug_solution_uom="g",
        ),
        actor_id,
    )
    operation = await db.get(DdcpProcessOperation, run_receipt.aggregate_id)
    assert operation.operation_type == "COATING_RUN"
    assert operation.state == "EXECUTION"

    not_effective_batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-NOTREADY-1")
    try:
        await coated_device_commands.evaluate_coating_run_readiness(db, batch_id=not_effective_batch.id, profile_version_id=uuid.uuid4())
        raised = False
    except CoatedDeviceProfileNotEffectiveError:
        raised = True
    assert raised


async def test_process_evidence_excursion_holds_run_and_complete_requires_dual_reconciliation(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_rule(db, actor_id, rule_id=PARAM_RULE_ID, expression_ast=PARAM_RULE_AST)
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="COAT-PARAM")
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-PARAM-1")
    substrate_lot = await _create_material_lot(db, seeded, code="SUBSTRATE-2", actor_id=actor_id)
    coating_drug_batch = await _create_batch(db, seeded, batch_number="BULK-COATING-DRUG-2")
    coating_drug_batch.status = "released"
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, substrate_lot, coating_drug_batch)

    run_receipt = await coated_device_commands.start_coating_run(
        db, coated_device_commands.StartCoatingRunCommand(idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, initial_drug_solution_quantity="200.0", initial_drug_solution_uom="g"), actor_id,
    )
    operation = await db.get(DdcpProcessOperation, run_receipt.aggregate_id)

    await coated_device_commands.record_coating_process_evidence(
        db, coated_device_commands.RecordCoatingProcessEvidenceCommand(idempotency_key=idem(), operation_id=operation.id, expected_version=operation.version, parameter_code="SPRAY_RATE", value="99", uom="ml/min", acceptance_rule_id=PARAM_RULE_ID), actor_id,
    )
    await db.refresh(operation)
    assert operation.state == "HOLD"
    assert operation.requires_deviation is True
    assert operation.process_parameters["readings"][0]["excursion"] is True

    try:
        await coated_device_commands.complete_coating_run(
            db, coated_device_commands.CompleteCoatingRunCommand(idempotency_key=idem(), operation_id=operation.id, expected_version=operation.version), actor_id,
        )
        raised = False
    except CoatingReconciliationFailedError:
        raised = True
    assert raised


async def test_bind_device_to_coating_rejects_duplicate_and_completes_run(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="COAT-BIND")
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-BIND-1")
    substrate_lot = await _create_material_lot(db, seeded, code="SUBSTRATE-3", actor_id=actor_id)
    coating_drug_batch = await _create_batch(db, seeded, batch_number="BULK-COATING-DRUG-3")
    coating_drug_batch.status = "released"
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, substrate_lot, coating_drug_batch)

    run_receipt = await coated_device_commands.start_coating_run(
        db, coated_device_commands.StartCoatingRunCommand(idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, initial_drug_solution_quantity="300.0", initial_drug_solution_uom="g"), actor_id,
    )
    operation = await db.get(DdcpProcessOperation, run_receipt.aggregate_id)

    device_ref = {"unit_id": str(uuid.uuid4())}
    binding_receipt = await coated_device_commands.bind_device_to_coating_constituent(
        db, coated_device_commands.BindDeviceToCoatingConstituentCommand(idempotency_key=idem(), batch_id=batch.id, device_unit_reference=device_ref, coating_solution_reference={"lot_id": str(uuid.uuid4())}), actor_id,
    )
    binding = await db.get(DdcpUnitBinding, binding_receipt.aggregate_id)
    assert binding.binding_type == "DEVICE_TO_COATING_CONSTITUENT"

    try:
        await coated_device_commands.bind_device_to_coating_constituent(
            db, coated_device_commands.BindDeviceToCoatingConstituentCommand(idempotency_key=idem(), batch_id=batch.id, device_unit_reference=device_ref, coating_solution_reference={"lot_id": str(uuid.uuid4())}), actor_id,
        )
        raised = False
    except DeviceToCoatingBindingAlreadyUsedError:
        raised = True
    assert raised

    await ddcp_commands.record_syringe_unit_or_count(
        db, ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="COATED", source="MANUAL", quantity=15), actor_id,
    )
    await coated_device_commands.complete_coating_run(
        db, coated_device_commands.CompleteCoatingRunCommand(idempotency_key=idem(), operation_id=operation.id, expected_version=operation.version), actor_id,
    )
    await db.refresh(operation)
    assert operation.state == "COMPLETE"


async def test_drug_loading_result_post_sterilization_test_and_release_readiness(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_rule(db, actor_id, rule_id=LOADING_RULE_ID, expression_ast=LOADING_RULE_AST)
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-LOAD-1")
    substrate_lot = await _create_material_lot(db, seeded, code="SUBSTRATE-4", actor_id=actor_id)
    coating_drug_batch = await _create_batch(db, seeded, batch_number="BULK-COATING-DRUG-4")
    coating_drug_batch.status = "released"
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, substrate_lot, coating_drug_batch)

    readiness = await coated_device_commands.evaluate_coated_device_release_readiness(db, batch.id, actor_id)
    assert readiness["ready"] is True

    fail_receipt = await coated_device_commands.record_drug_loading_result(
        db, coated_device_commands.RecordDrugLoadingResultCommand(idempotency_key=idem(), batch_id=batch.id, unit_or_sample_id="U-1", measured_value="0.5", uom="mg/cm2", acceptance_rule_id=LOADING_RULE_ID), actor_id,
    )
    link = await db.get(DeviceFunctionalTestLink, fail_receipt.aggregate_id)
    assert link.result_state == "OOS"

    await coated_device_commands.record_post_sterilization_test(
        db,
        coated_device_commands.RecordPostSterilizationTestCommand(
            idempotency_key=idem(), batch_id=batch.id, sterilization_reference={"cycle_id": str(uuid.uuid4())}, test_type="DRUG_CONTENT_ASSAY", result_state="PASS",
        ),
        actor_id,
    )

    readiness_after = await coated_device_commands.evaluate_coated_device_release_readiness(db, batch.id, actor_id)
    assert readiness_after["ready"] is False
    assert readiness_after["checkpoints"]["DEVICE_CONSTITUENT"]["state"] == "BLOCKED"


async def test_evidence_package_and_complaint_trace(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-TRACE-1")
    substrate_lot = await _create_material_lot(db, seeded, code="SUBSTRATE-5", actor_id=actor_id)
    coating_drug_batch = await _create_batch(db, seeded, batch_number="BULK-COATING-DRUG-5")
    coating_drug_batch.status = "released"
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, substrate_lot, coating_drug_batch)

    await coated_device_commands.record_drug_coating_usage(
        db, coated_device_commands.RecordDrugCoatingUsageCommand(idempotency_key=idem(), batch_id=batch.id, usage_type="ISSUED", quantity="100.0", uom="g"), actor_id,
    )

    package_receipt = await coated_device_commands.create_coated_device_batch_evidence_package(
        db, coated_device_commands.CreateCoatedDeviceBatchEvidencePackageCommand(idempotency_key=idem(), batch_id=batch.id), actor_id,
    )
    assert package_receipt.resulting_version == 1

    trace = await coated_device_commands.trace_coated_device_complaint(db, batch.id)
    assert trace["batch_id"] == str(batch.id)
    assert len(trace["substrate_and_drug_handoffs"]) == 2
    assert len(trace["drug_coating_usage"]) == 1


# =======================================================================================================
# Document 57 remaining gaps closed this pass: COAT-FR-004/007/008/013/015/016/017/018/022/025/029.
# COAT-FR-021 (packaging, blocked by SG-149) and COAT-FR-023 (process sampling -- no existing field
# carries a sampling-location taxonomy without inventing one) stay NOT_STARTED -- not guessed.
# =======================================================================================================


async def test_surface_prep_drying_curing_and_equipment_bound_run(seeded, db):
    """COAT-FR-004 (surface preparation), COAT-FR-017 (drying/curing) -- both reuse device_assembly_record
    with the extended ASSEMBLY_STEPS vocabulary (SG-150). COAT-FR-007 (equipment/program bound to batch)
    -- start_coating_run()'s existing equipment_id param, exercised with a real EquipmentAsset fixture
    for the first time in this test file."""

    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="COAT-PREP")
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-PREP-1")
    substrate_lot = await _create_material_lot(db, seeded, code="SUBSTRATE-PREP-1", actor_id=actor_id)
    coating_drug_batch = await _create_batch(db, seeded, batch_number="BULK-COATING-DRUG-PREP-1")
    coating_drug_batch.status = "released"
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, substrate_lot, coating_drug_batch)

    prep_receipt = await ddcp_commands.record_device_assembly_step(
        db, ddcp_commands.RecordDeviceAssemblyStepCommand(idempotency_key=idem(), batch_id=batch.id, assembly_step="SURFACE_PREPARATION", component_lot_reference={"lot_id": str(uuid.uuid4())}), actor_id,
    )
    prep_record = await db.get(DeviceAssemblyRecord, prep_receipt.aggregate_id)
    assert prep_record.assembly_step == "SURFACE_PREPARATION"

    cure_receipt = await ddcp_commands.record_device_assembly_step(
        db, ddcp_commands.RecordDeviceAssemblyStepCommand(idempotency_key=idem(), batch_id=batch.id, assembly_step="DRYING_CURING", component_lot_reference={"lot_id": str(uuid.uuid4())}), actor_id,
    )
    cure_record = await db.get(DeviceAssemblyRecord, cure_receipt.aggregate_id)
    assert cure_record.assembly_step == "DRYING_CURING"

    equipment = EquipmentAsset(site_id=seeded["site_id"], equipment_code="COATER-1", state="QUALIFIED_AVAILABLE", qualification_status="QUALIFIED", version=1)
    db.add(equipment)
    await db.flush()
    run_receipt = await coated_device_commands.start_coating_run(
        db,
        coated_device_commands.StartCoatingRunCommand(
            idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, equipment_id=equipment.id,
            program_id="COAT-PROG-1", program_version="v2", initial_drug_solution_quantity="150.0", initial_drug_solution_uom="g",
        ),
        actor_id,
    )
    operation = await db.get(DdcpProcessOperation, run_receipt.aggregate_id)
    assert operation.equipment_id == equipment.id
    assert operation.program_id == "COAT-PROG-1"


async def test_environment_gate_blocks_readiness_when_not_ready(seeded, db):
    """COAT-FR-008: environment readiness gate, same caller-supplied-snapshot discipline as Document 56's
    INH-FR-018 (never a baked-in threshold, Document 57 §7: 'No generic sterilization assumption is
    allowed' -- the same restraint extends to the environment gate)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    profile_receipt = await coated_device_commands.create_coated_device_profile_version(
        db,
        coated_device_commands.CreateCoatedDeviceProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], profile_code="COAT-ENV-1", environment_profile_id="ENV-COATING-STANDARD",
            constituent_requirements=[
                {"constituent_type": "DEVICE", "component_role": "substrate", "required_state": "RELEASED"},
                {"constituent_type": "DRUG", "component_role": "coating_solution", "required_state": "RELEASED"},
            ],
        ),
        actor_id,
    )
    profile_id = profile_receipt.aggregate_id
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=profile_id, expected_version=1), actor_id,
    )
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-ENV-1")
    substrate_lot = await _create_material_lot(db, seeded, code="SUBSTRATE-ENV-1", actor_id=actor_id)
    coating_drug_batch = await _create_batch(db, seeded, batch_number="BULK-COATING-DRUG-ENV-1")
    coating_drug_batch.status = "released"
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, substrate_lot, coating_drug_batch)

    ready_check = await coated_device_commands.evaluate_coating_run_readiness(db, batch_id=batch.id, profile_version_id=profile_id, environment_status={"ready": True})
    assert ready_check["ready"] is True

    not_ready_check = await coated_device_commands.evaluate_coating_run_readiness(db, batch_id=batch.id, profile_version_id=profile_id, environment_status={"ready": False, "particle_count": 999})
    assert not_ready_check["ready"] is False
    assert any(b["code"] == "COATING_ENVIRONMENT_NOT_READY" for b in not_ready_check["blockers"])


async def test_device_functional_test_covers_integrity_elution_and_dimensional(seeded, db):
    """COAT-FR-013 (coating integrity inspection defect), COAT-FR-015 (release/elution profile),
    COAT-FR-016 (dimensional/device function) -- all reuse record_device_functional_test() (new, plain
    non-rule-evaluated device_functional_test_link writer, SG-150)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-FUNCTEST-1")

    integrity_receipt = await coated_device_commands.record_device_functional_test(
        db,
        coated_device_commands.RecordDeviceFunctionalTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="COATING_INTEGRITY",
            qc_record_reference={"record_id": str(uuid.uuid4()), "defect_code": "DELAMINATION"}, result_state="FAIL",
        ),
        actor_id,
    )
    integrity_link = await db.get(DeviceFunctionalTestLink, integrity_receipt.aggregate_id)
    assert integrity_link.qc_record_reference["defect_code"] == "DELAMINATION"
    assert integrity_link.result_state == "FAIL"

    await coated_device_commands.record_device_functional_test(
        db,
        coated_device_commands.RecordDeviceFunctionalTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="RELEASE_ELUTION", qc_record_reference={"record_id": str(uuid.uuid4())},
            method_reference={"method_id": "USP-711"}, result_state="PASS",
        ),
        actor_id,
    )
    await coated_device_commands.record_device_functional_test(
        db,
        coated_device_commands.RecordDeviceFunctionalTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="DIMENSIONAL_FUNCTION", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="PASS",
        ),
        actor_id,
    )

    links = (await db.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch.id))).scalars().all()
    assert {l.test_type for l in links} == {"COATING_INTEGRITY", "RELEASE_ELUTION", "DIMENSIONAL_FUNCTION"}


async def test_sterilization_interaction_captured_on_profile(seeded, db):
    """COAT-FR-018: 'The profile must state whether coating occurs before/after sterilization; sterilization
    modality/profile...' -- sterilizationRouteId is captured on the profile's own constituent_architecture
    at creation time; no generic sterilization assumption is made when it's left unset (Document 57 §7)."""

    actor_id = seeded["users"]["ddcp.engineer"].id

    with_sterilization = await coated_device_commands.create_coated_device_profile_version(
        db,
        coated_device_commands.CreateCoatedDeviceProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], profile_code="COAT-STERIL-1", sterilization_route_id="EO-CYCLE-A",
            constituent_requirements=[{"constituent_type": "DEVICE", "component_role": "substrate", "required_state": "RELEASED"}],
        ),
        actor_id,
    )
    profile = await db.get(DdcpProfileVersion, with_sterilization.aggregate_id)
    assert profile.constituent_architecture["sterilizationRouteId"] == "EO-CYCLE-A"

    without_sterilization = await coated_device_commands.create_coated_device_profile_version(
        db,
        coated_device_commands.CreateCoatedDeviceProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], profile_code="COAT-NOSTERIL-1",
            constituent_requirements=[{"constituent_type": "DEVICE", "component_role": "substrate", "required_state": "RELEASED"}],
        ),
        actor_id,
    )
    profile2 = await db.get(DdcpProfileVersion, without_sterilization.aggregate_id)
    assert profile2.constituent_architecture["sterilizationRouteId"] is None


async def test_device_to_coating_binding_carries_unit_serial(seeded, db):
    """COAT-FR-022: unit-level coated device trace -- the device_unit_reference already carries whatever
    serial/unit identifier the caller supplies (JSONB reference, no invented UDI format), round-tripped
    through the binding record."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-SERIAL-1")

    receipt = await coated_device_commands.bind_device_to_coating_constituent(
        db,
        coated_device_commands.BindDeviceToCoatingConstituentCommand(
            idempotency_key=idem(), batch_id=batch.id, device_unit_reference={"unit_id": str(uuid.uuid4()), "unit_serial": "COAT-SN-0001"},
            coating_solution_reference={"lot_id": str(uuid.uuid4())},
        ),
        actor_id,
    )
    binding = await db.get(DdcpUnitBinding, receipt.aggregate_id)
    assert binding.primary_unit_reference["unit_serial"] == "COAT-SN-0001"


async def test_coated_device_disposition_requires_reason_and_dual_rework_evidence(seeded, db):
    """COAT-FR-025: 'Recoating/stripping/reprocessing default prohibited unless released validated route
    explicitly permits and drug/device impact assessed' -- REWORK requires BOTH a rework_procedure_reference
    AND a drug_device_impact_assessment, not just one (a stricter default-disallow than PFS-FR-027/
    INJ-FR-022, matching this document's own explicit 'impact assessed' text)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-COAT-DISP-1")

    try:
        await coated_device_commands.record_coated_device_disposition(
            db, coated_device_commands.RecordCoatedDeviceDispositionCommand(idempotency_key=idem(), batch_id=batch.id, unit_identifier="COAT-SN-1000", result="REJECT"), actor_id,
        )
        raised = False
    except ValidationFailedError:
        raised = True
    assert raised

    try:
        await coated_device_commands.record_coated_device_disposition(
            db,
            coated_device_commands.RecordCoatedDeviceDispositionCommand(
                idempotency_key=idem(), batch_id=batch.id, unit_identifier="COAT-SN-1000", result="REWORK", reason="Coating thickness excursion",
                rework_procedure_reference={"procedure_id": "SOP-COAT-REWORK-1"},
            ),
            actor_id,
        )
        raised = False
    except ReworkRouteRequiredError:
        raised = True
    assert raised

    receipt = await coated_device_commands.record_coated_device_disposition(
        db,
        coated_device_commands.RecordCoatedDeviceDispositionCommand(
            idempotency_key=idem(), batch_id=batch.id, unit_identifier="COAT-SN-1000", result="REWORK", reason="Coating thickness excursion",
            rework_procedure_reference={"procedure_id": "SOP-COAT-REWORK-1"}, drug_device_impact_assessment={"impact": "none", "assessed_by": str(actor_id)},
        ),
        actor_id,
    )
    record = await db.get(DeviceAssemblyRecord, receipt.aggregate_id)
    assert record.assembly_step == "FINAL_DISPOSITION"
    assert record.result == "REWORK"


async def test_change_linkage_reused_for_coated_device_profile(seeded, db):
    """COAT-FR-029: the write path already exists (qms.change_commands.assess_impact's own generic
    affected_objects list, reused verbatim from Document 54) -- confirms get_ddcp_change_linkage() (also
    reused verbatim) round-trips for a coated-device profile object_type."""

    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="COAT-CHANGE-1")

    change_receipt = await change_commands.create_change(
        db,
        change_commands.CreateChangeCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], change_number="CHG-COAT-1", change_type="material",
            classification="permanent", current_state={"coating_formulation": "v1"}, proposed_state={"coating_formulation": "v2"},
            reason="Coating formulation change", owner_subject_id=actor_id,
        ),
        actor_id,
    )
    await change_commands.assess_impact(
        db,
        change_commands.AssessImpactCommand(
            idempotency_key=idem(), change_id=change_receipt.aggregate_id, expected_version=1,
            affected_objects=[{"object_type": "ddcp_profile_version", "object_id": str(profile.id), "impact_category": "risk", "action_required": "Re-validate drug loading and release/elution profile"}],
        ),
        actor_id,
    )
    linkage = await ddcp_commands.get_ddcp_change_linkage(db, "ddcp_profile_version", profile.id)
    assert len(linkage["changes"]) == 1
    assert linkage["changes"][0]["change_number"] == "CHG-COAT-1"
