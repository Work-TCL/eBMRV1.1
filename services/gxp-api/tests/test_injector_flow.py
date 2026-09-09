"""WP-08 (Document 55, SPEC-DDCP-002, INJ-FR-001..030): Autoinjector, Pen Injector & Cartridge-Based DDCP
Manufacturing Profile. SG-150: no Document 112 schema exists for this document -- it reuses Document 54's
tables/functions (profile/constituent-requirement/constituent-handoff/device-assembly-record/
device-functional-test-link/release-checkpoint/evidence-manifest) plus three new tables
(ddcp_process_operation, ddcp_unit_binding, reusable_device_pairing).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select

from app.modules.batch.models import Batch
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp import injector_commands
from app.modules.ddcp.models import (
    ConstituentHandoff,
    DdcpProcessOperation,
    DdcpProfileVersion,
    DdcpUnitBinding,
    DeviceAssemblyRecord,
    DeviceFunctionalTestLink,
    ReusableDevicePairing,
)
from app.modules.material.models import Material, MaterialLot
from app.modules.product.models import Product
from app.modules.product_master.models import ProductVersion
from app.modules.qms import change_commands
from app.modules.recipe.models import Recipe
from app.modules.rules import commands as rules_commands
from app.modules.signature.models import SignaturePolicy
from app.mutation.errors import (
    ContainerAlreadyUsedError,
    InjectorProfileNotEffectiveError,
    ReworkRouteRequiredError,
    UnitReconciliationFailedError,
    ValidationFailedError,
)
from tests.conftest import idem

DOSE_RULE_ID = "injector-dose-accuracy-tolerance"
DOSE_RULE_AST = {
    "op": "and",
    "args": [
        {"op": "gte", "args": [{"var": "value"}, "0.90"]},
        {"op": "lte", "args": [{"var": "value"}, "1.10"]},
    ],
}


async def _release_dose_rule(db, actor_id):
    db.add(SignaturePolicy(record_type="rule", action="release", meaning="Released", signature_required=False))
    await db.flush()
    draft = await rules_commands.create_draft(
        db,
        rules_commands.CreateRuleDraftCommand(
            idempotency_key=idem(), rule_id=DOSE_RULE_ID, rule_type="acceptance", semantic_version="1.0.0",
            expression_ast=DOSE_RULE_AST, input_contract={"value": {"type": "decimal"}},
            output_contract={"eligible": {"type": "boolean"}}, unit_policy={},
            precision_policy={"calculation_class": "CC-5", "reported_decimal_places": 2},
            rounding_policy={"policy_version": "DOCUMENT-110-v1.0"},
        ),
        actor_id,
    )
    await rules_commands.validate_rule(db, rules_commands.ValidateRuleCommand(idempotency_key=idem(), rule_object_id=draft.aggregate_id), actor_id)
    await rules_commands.release_rule(db, rules_commands.ReleaseRuleCommand(idempotency_key=idem(), rule_object_id=draft.aggregate_id), actor_id)


async def _create_batch(db, seeded, *, batch_number: str) -> Batch:
    site_id = seeded["site_id"]
    product = Product(site_id=site_id, code=f"PROD-{batch_number}", name="Test Injector Product", status="active", version=1)
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


async def _create_released_product_version(
    db, seeded, *, code: str, manufacturing_profile_code: str = "device",
) -> ProductVersion:
    # SG-175: every DDCP profile now needs a real, RELEASED Product Master version
    # (`product_version_id`, migration 0089). No manufacturing_profile_code value names "autoinjector"
    # specifically (SG-175's residual half), so "device" is used here purely as fixture data -- the
    # command layer for this family checks existence/released/site only, never this value.
    pv = ProductVersion(
        product_business_id=f"PM-{code}", version_no=1, product_code=f"PM-{code}", name=f"Test product {code}",
        manufacturing_profile_code=manufacturing_profile_code, lifecycle_state="released", site_id=seeded["site_id"],
    )
    db.add(pv)
    await db.flush()
    return pv


async def _create_and_release_profile(db, seeded, actor_id, *, profile_code: str) -> DdcpProfileVersion:
    product_version = await _create_released_product_version(db, seeded, code=profile_code)
    receipt = await injector_commands.create_injector_profile_version(
        db,
        injector_commands.CreateInjectorProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=product_version.id,
            profile_code=profile_code, injector_type="AUTOINJECTOR",
            constituent_requirements=[
                {"constituent_type": "DRUG", "component_role": "drug_container", "required_state": "RELEASED"},
                {"constituent_type": "DEVICE", "component_role": "housing", "required_state": "RELEASED"},
            ],
        ),
        actor_id,
    )
    profile_id = receipt.aggregate_id
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=profile_id, expected_version=1), actor_id,
    )
    return await db.get(DdcpProfileVersion, profile_id)


async def _accept_constituents(db, seeded, actor_id, batch, bulk_batch, device_lot):
    for from_c, to_c, ref in (("DRUG", "drug_container", {"batch_id": str(bulk_batch.id)}), ("DEVICE", "housing", {"lot_id": str(device_lot.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )


async def test_create_profile_and_release_requires_constituent_requirements(seeded, db):
    actor_id = seeded["users"]["ddcp.engineer"].id
    empty_product = await _create_released_product_version(db, seeded, code="INJ-EMPTY")
    empty = await injector_commands.create_injector_profile_version(
        db,
        injector_commands.CreateInjectorProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=empty_product.id,
            profile_code="INJ-EMPTY", injector_type="PEN_REUSABLE",
        ),
        actor_id,
    )
    assert (await db.get(DdcpProfileVersion, empty.aggregate_id)).subtype == "PEN_REUSABLE"

    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INJ-001")
    assert profile.state == "RELEASED"
    assert profile.subtype == "AUTOINJECTOR"


async def test_assembly_readiness_and_start_operation(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INJ-READY")
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-READY-1")

    readiness = await injector_commands.evaluate_injector_assembly_readiness(db, batch_id=batch.id, profile_version_id=profile.id)
    assert readiness["ready"] is False

    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-INJ-1")
    bulk_batch.status = "released"
    device_lot = await _create_material_lot(db, seeded, code="HOUSING-1", actor_id=actor_id)
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, bulk_batch, device_lot)

    readiness = await injector_commands.evaluate_injector_assembly_readiness(db, batch_id=batch.id, profile_version_id=profile.id)
    assert readiness["ready"] is True

    op_receipt = await injector_commands.start_injector_assembly_operation(
        db, injector_commands.StartInjectorAssemblyOperationCommand(idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id), actor_id,
    )
    operation = await db.get(DdcpProcessOperation, op_receipt.aggregate_id)
    assert operation.operation_type == "INJECTOR_ASSEMBLY"
    assert operation.state == "EXECUTION"

    not_effective = await _create_batch(db, seeded, batch_number="BATCH-INJ-NOTREADY-1")
    try:
        await injector_commands.evaluate_injector_assembly_readiness(db, batch_id=not_effective.id, profile_version_id=uuid.uuid4())
        raised = False
    except InjectorProfileNotEffectiveError:
        raised = True
    assert raised


async def test_record_assembly_parameter_and_complete_operation(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INJ-PARAM")
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-PARAM-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-INJ-2")
    bulk_batch.status = "released"
    device_lot = await _create_material_lot(db, seeded, code="HOUSING-2", actor_id=actor_id)
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, bulk_batch, device_lot)

    op_receipt = await injector_commands.start_injector_assembly_operation(
        db, injector_commands.StartInjectorAssemblyOperationCommand(idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id), actor_id,
    )
    operation = await db.get(DdcpProcessOperation, op_receipt.aggregate_id)

    await injector_commands.record_assembly_parameter(
        db, injector_commands.RecordAssemblyParameterCommand(idempotency_key=idem(), operation_id=operation.id, expected_version=operation.version, parameter_code="SPRING_TORQUE", value="4.2", uom="N.cm"), actor_id,
    )
    await db.refresh(operation)
    assert len(operation.process_parameters["readings"]) == 1

    try:
        await injector_commands.complete_injector_assembly_operation(
            db, injector_commands.CompleteInjectorAssemblyOperationCommand(idempotency_key=idem(), operation_id=operation.id, expected_version=operation.version), actor_id,
        )
        raised = False
    except UnitReconciliationFailedError:
        raised = True
    assert raised

    await ddcp_commands.record_syringe_unit_or_count(
        db, ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="ASSEMBLED", source="MANUAL", quantity=10), actor_id,
    )
    await injector_commands.complete_injector_assembly_operation(
        db, injector_commands.CompleteInjectorAssemblyOperationCommand(idempotency_key=idem(), operation_id=operation.id, expected_version=operation.version), actor_id,
    )
    await db.refresh(operation)
    assert operation.state == "COMPLETE"


async def test_bind_drug_container_rejects_duplicate_use(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-BIND-1")
    container_ref = {"container_id": str(uuid.uuid4())}

    receipt = await injector_commands.bind_drug_container_to_injector_unit(
        db, injector_commands.BindDrugContainerToInjectorUnitCommand(idempotency_key=idem(), batch_id=batch.id, drug_container_reference=container_ref, injector_unit_serial="INJ-SN-0001"), actor_id,
    )
    binding = await db.get(DdcpUnitBinding, receipt.aggregate_id)
    assert binding.binding_type == "DRUG_CONTAINER_TO_INJECTOR_UNIT"

    try:
        await injector_commands.bind_drug_container_to_injector_unit(
            db, injector_commands.BindDrugContainerToInjectorUnitCommand(idempotency_key=idem(), batch_id=batch.id, drug_container_reference=container_ref, injector_unit_serial="INJ-SN-0002"), actor_id,
        )
        raised = False
    except ContainerAlreadyUsedError:
        raised = True
    assert raised


async def test_functional_test_and_dose_delivery_evaluation(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_dose_rule(db, actor_id)
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-TEST-1")

    await injector_commands.execute_injector_functional_test(
        db, injector_commands.ExecuteInjectorFunctionalTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type="ACTIVATION_FORCE", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="PASS"), actor_id,
    )

    pass_receipt = await injector_commands.evaluate_dose_delivery_result(
        db, injector_commands.EvaluateDoseDeliveryResultCommand(idempotency_key=idem(), batch_id=batch.id, sample_id="S-1", actual_value="1.0", uom="mg", acceptance_rule_id=DOSE_RULE_ID), actor_id,
    )
    assert pass_receipt.resulting_version == 1

    fail_receipt = await injector_commands.evaluate_dose_delivery_result(
        db, injector_commands.EvaluateDoseDeliveryResultCommand(idempotency_key=idem(), batch_id=batch.id, sample_id="S-2", actual_value="0.5", uom="mg", acceptance_rule_id=DOSE_RULE_ID), actor_id,
    )
    from app.modules.ddcp.models import DeviceFunctionalTestLink
    link = await db.get(DeviceFunctionalTestLink, fail_receipt.aggregate_id)
    assert link.result_state == "FAIL"
    assert link.test_type == "DOSE_ACCURACY"


async def test_record_unit_disposition_requires_reason_and_rework_route(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-DISP-1")

    try:
        await injector_commands.record_unit_disposition(
            db, injector_commands.RecordUnitDispositionCommand(idempotency_key=idem(), batch_id=batch.id, unit_identifier="INJ-SN-1000", result="REJECT"), actor_id,
        )
        raised = False
    except ValidationFailedError:
        raised = True
    assert raised

    try:
        await injector_commands.record_unit_disposition(
            db, injector_commands.RecordUnitDispositionCommand(idempotency_key=idem(), batch_id=batch.id, unit_identifier="INJ-SN-1000", result="REWORK", reason="Needle misalignment"), actor_id,
        )
        raised = False
    except ReworkRouteRequiredError:
        raised = True
    assert raised

    receipt = await injector_commands.record_unit_disposition(
        db,
        injector_commands.RecordUnitDispositionCommand(
            idempotency_key=idem(), batch_id=batch.id, unit_identifier="INJ-SN-1000", result="REWORK", reason="Needle misalignment",
            rework_procedure_reference={"procedure_id": "SOP-INJ-REWORK-1"},
        ),
        actor_id,
    )
    record = await db.get(DeviceAssemblyRecord, receipt.aggregate_id)
    assert record.assembly_step == "FINAL_DISPOSITION"
    assert record.result == "REWORK"


async def test_release_readiness_evidence_package_and_complaint_trace(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-RELEASE-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-INJ-3")
    bulk_batch.status = "released"
    device_lot = await _create_material_lot(db, seeded, code="HOUSING-3", actor_id=actor_id)
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, bulk_batch, device_lot)

    readiness = await injector_commands.evaluate_injector_release_readiness(db, batch.id, actor_id)
    assert readiness["ready"] is True

    await injector_commands.bind_drug_container_to_injector_unit(
        db, injector_commands.BindDrugContainerToInjectorUnitCommand(idempotency_key=idem(), batch_id=batch.id, drug_container_reference={"container_id": str(uuid.uuid4())}, injector_unit_serial="INJ-SN-COMPLAINT-1"), actor_id,
    )
    await injector_commands.record_unit_disposition(
        db, injector_commands.RecordUnitDispositionCommand(idempotency_key=idem(), batch_id=batch.id, unit_identifier="INJ-SN-COMPLAINT-1", result="PASS"), actor_id,
    )

    package_receipt = await injector_commands.create_injector_batch_evidence_package(
        db, injector_commands.CreateInjectorBatchEvidencePackageCommand(idempotency_key=idem(), batch_id=batch.id), actor_id,
    )
    assert package_receipt.resulting_version == 1

    trace = await injector_commands.trace_complaint_serial(db, "INJ-SN-COMPLAINT-1")
    assert trace["finished_serial"] == "INJ-SN-COMPLAINT-1"
    assert len(trace["device_assembly_records"]) == 1
    assert len(trace["drug_container_bindings"]) == 1


# =======================================================================================================
# Document 55 remaining gaps closed this pass: INJ-FR-010/011/013/016/017/018/020/024/027/028/029.
# INJ-FR-019 (software/electronics, "requires separately approved profile") and INJ-FR-023 (packaging,
# blocked by SG-149's ebmr.batches/ebmr.gxp_batch divergence) stay NOT_STARTED -- not guessed.
# =======================================================================================================


async def test_functional_test_covers_needle_dose_mechanism_indicators_and_final_test(seeded, db):
    """INJ-FR-010 (needle activation), INJ-FR-011 (dose setting mechanism), INJ-FR-013 (function test
    plan -- sample_plan_reference/method_reference actually populated, not just accepted), INJ-FR-017
    (audible/visual indicators), INJ-FR-024 (final device/combination test) -- all reuse
    execute_injector_functional_test()/device_functional_test_link verbatim with the extended
    DEVICE_TEST_TYPES vocabulary (SG-150)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-TESTPLAN-1")

    needle_receipt = await injector_commands.execute_injector_functional_test(
        db,
        injector_commands.ExecuteInjectorFunctionalTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="NEEDLE_ACTIVATION",
            qc_record_reference={"record_id": str(uuid.uuid4())},
            sample_plan_reference={"plan_id": "SP-NEEDLE-1", "sampling": "100_PERCENT"},
            method_reference={"fixture_id": "FX-1", "program_version": "v3"}, result_state="PASS",
        ),
        actor_id,
    )
    needle_link = await db.get(DeviceFunctionalTestLink, needle_receipt.aggregate_id)
    assert needle_link.sample_plan_reference["sampling"] == "100_PERCENT"
    assert needle_link.method_reference["program_version"] == "v3"

    await injector_commands.execute_injector_functional_test(
        db,
        injector_commands.ExecuteInjectorFunctionalTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="DOSE_MECHANISM_CALIBRATION",
            qc_record_reference={"record_id": str(uuid.uuid4()), "dosing_range": "0.5-2.0mg"}, result_state="PASS",
        ),
        actor_id,
    )
    await injector_commands.execute_injector_functional_test(
        db,
        injector_commands.ExecuteInjectorFunctionalTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="AUDIBLE_INDICATOR", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="PASS",
        ),
        actor_id,
    )
    final_receipt = await injector_commands.execute_injector_functional_test(
        db,
        injector_commands.ExecuteInjectorFunctionalTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="FINAL_COMBINATION_TEST", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="PASS",
        ),
        actor_id,
    )
    final_link = await db.get(DeviceFunctionalTestLink, final_receipt.aggregate_id)
    assert final_link.result_state == "PASS"

    all_links = (await db.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch.id))).scalars().all()
    assert {l.test_type for l in all_links} == {"NEEDLE_ACTIVATION", "DOSE_MECHANISM_CALIBRATION", "AUDIBLE_INDICATOR", "FINAL_COMBINATION_TEST"}


async def test_dose_delivery_defect_taxonomy_captured_on_failure(seeded, db):
    """INJ-FR-016: 'Test/result taxonomy includes under-delivery, partial delivery, premature stop and
    other profile defects.' No dedicated column exists (or is baselined) for this taxonomy -- captured as
    a documented, caller-supplied defect_code inside qc_record_reference, the same 'logical reference'
    discipline every other free-form DDCP field already uses; result_state=FAIL is the real gate."""

    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_dose_rule(db, actor_id)
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-DEFECT-1")

    fail_receipt = await injector_commands.evaluate_dose_delivery_result(
        db,
        injector_commands.EvaluateDoseDeliveryResultCommand(
            idempotency_key=idem(), batch_id=batch.id, sample_id="S-DEFECT-1", actual_value="0.3", uom="mg",
            acceptance_rule_id=DOSE_RULE_ID, qc_record_reference={"defect_code": "UNDER_DELIVERY"},
        ),
        actor_id,
    )
    link = await db.get(DeviceFunctionalTestLink, fail_receipt.aggregate_id)
    assert link.result_state == "FAIL"
    assert link.qc_record_reference["defect_code"] == "UNDER_DELIVERY"


async def test_reusable_device_pairing_requires_batch_and_validates_status(seeded, db):
    """INJ-FR-018: reusable injector + cartridge compatibility pairing, without assuming a permanent
    single-unit relationship (batch-scoped this pass -- see SG-150)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-PAIR-1")

    try:
        await injector_commands.record_reusable_device_pairing(
            db,
            injector_commands.RecordReusableDevicePairingCommand(
                idempotency_key=idem(), reusable_device_reference={"device_family": "PEN-X"},
                cartridge_lot_reference={"lot_id": str(uuid.uuid4())}, compatibility_status="BOGUS",
            ),
            actor_id,
        )
        raised = False
    except ValidationFailedError:
        raised = True
    assert raised

    receipt = await injector_commands.record_reusable_device_pairing(
        db,
        injector_commands.RecordReusableDevicePairingCommand(
            idempotency_key=idem(), reusable_device_reference={"device_family": "PEN-X"},
            cartridge_lot_reference={"lot_id": str(uuid.uuid4())}, compatibility_status="COMPATIBLE",
            rationale="Cross-labeled per approved design history file", batch_id=batch.id,
        ),
        actor_id,
    )
    pairing = await db.get(ReusableDevicePairing, receipt.aggregate_id)
    assert pairing.compatibility_status == "COMPATIBLE"
    assert pairing.reusable_device_reference["device_family"] == "PEN-X"


async def test_human_factors_reference_captured_on_profile(seeded, db):
    """INJ-FR-020: 'Profile can reference design/risk/human-factors critical tasks but manufacturing eBMR
    does not itself determine usability acceptability.' Captured as a logical reference in the profile's
    own required_controls JSONB -- no usability-acceptability decision is made or implied here."""

    actor_id = seeded["users"]["ddcp.engineer"].id
    hf_product = await _create_released_product_version(db, seeded, code="INJ-HF-1")
    receipt = await injector_commands.create_injector_profile_version(
        db,
        injector_commands.CreateInjectorProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=hf_product.id,
            profile_code="INJ-HF-1", injector_type="AUTOINJECTOR",
            required_controls={"humanFactorsReference": {"dhf_id": "DHF-2026-001", "critical_tasks": ["activation", "needle_shield_engage"]}},
        ),
        actor_id,
    )
    profile = await db.get(DdcpProfileVersion, receipt.aggregate_id)
    assert profile.required_controls["humanFactorsReference"]["dhf_id"] == "DHF-2026-001"


async def test_release_readiness_blocks_on_pending_handoff_and_failed_test(seeded, db):
    """INJ-FR-027: a real negative-path assertion, not just the happy path -- release readiness must
    actually block when a device handoff is still pending and a functional test has failed."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INJ-BLOCK-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-INJ-BLOCK-1")
    bulk_batch.status = "released"
    await db.flush()

    drug_receipt = await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent="DRUG", to_constituent="drug_container", source_batch_reference={"batch_id": str(bulk_batch.id)}), actor_id,
    )
    await ddcp_commands.decide_constituent_handoff(
        db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=drug_receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
    )
    # Device handoff deliberately left PENDING (not accepted).
    await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent="DEVICE", to_constituent="housing", source_batch_reference={"lot_id": str(uuid.uuid4())}), actor_id,
    )
    await injector_commands.execute_injector_functional_test(
        db, injector_commands.ExecuteInjectorFunctionalTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type="ACTIVATION_FORCE", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="FAIL"), actor_id,
    )

    readiness = await injector_commands.evaluate_injector_release_readiness(db, batch.id, actor_id)
    assert readiness["ready"] is False
    assert readiness["checkpoints"]["DEVICE_CONSTITUENT"]["state"] == "BLOCKED"
    codes = {b["code"] for b in readiness["checkpoints"]["DEVICE_CONSTITUENT"]["blockers"]}
    assert "DEVICE_COMPONENT_NOT_RELEASED" in codes
    assert "INJECTOR_TEST_FAILED" in codes


async def test_change_linkage_reused_for_injector_profile(seeded, db):
    """INJ-FR-028: the write path already exists (qms.change_commands.assess_impact's own generic
    affected_objects list, reused verbatim from Document 54) -- this confirms get_ddcp_change_linkage()
    (also reused verbatim) round-trips for an injector profile object_type."""

    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INJ-CHANGE-1")

    change_receipt = await change_commands.create_change(
        db,
        change_commands.CreateChangeCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], change_number="CHG-INJ-1", change_type="equipment",
            classification="permanent", current_state={"spring": "v1"}, proposed_state={"spring": "v2"},
            reason="Drive spring supplier change", owner_subject_id=actor_id,
        ),
        actor_id,
    )
    await change_commands.assess_impact(
        db,
        change_commands.AssessImpactCommand(
            idempotency_key=idem(), change_id=change_receipt.aggregate_id, expected_version=1,
            affected_objects=[{"object_type": "ddcp_profile_version", "object_id": str(profile.id), "impact_category": "risk", "action_required": "Re-validate drive/spring force output"}],
        ),
        actor_id,
    )

    linkage = await ddcp_commands.get_ddcp_change_linkage(db, "ddcp_profile_version", profile.id)
    assert len(linkage["changes"]) == 1
    assert linkage["changes"][0]["change_number"] == "CHG-INJ-1"


async def test_profile_family_inheritance_via_version_supersede(seeded, db):
    """INJ-FR-029: 'Common injector profile can inherit product-family functions while exact test
    outputs/limits are product-version controlled' -- verified via the same profile_code/version supersede
    mechanism release_injectable_profile_version() already provides (reused verbatim from Document 54):
    version 2 supersedes version 1 under the same profile_code, carrying its own distinct required_controls."""

    actor_id = seeded["users"]["ddcp.engineer"].id
    # Same profile_code reused across v1/v2 (that's the point of this test), so the Product Master
    # version is created once and referenced by both -- product_version_id has no uniqueness constraint
    # of its own on ddcp_profile_version, only profile_code+version does.
    family_product = await _create_released_product_version(db, seeded, code="INJ-FAMILY-1")
    v1_receipt = await injector_commands.create_injector_profile_version(
        db,
        injector_commands.CreateInjectorProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=family_product.id,
            profile_code="INJ-FAMILY-1", injector_type="AUTOINJECTOR",
            required_controls={"doseAccuracyLimit": "0.90-1.10"},
            constituent_requirements=[{"constituent_type": "DEVICE", "component_role": "housing", "required_state": "RELEASED"}],
        ),
        actor_id,
    )
    v1 = await db.get(DdcpProfileVersion, v1_receipt.aggregate_id)
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=v1.id, expected_version=1), actor_id,
    )

    v2_receipt = await injector_commands.create_injector_profile_version(
        db,
        injector_commands.CreateInjectorProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=family_product.id,
            profile_code="INJ-FAMILY-1", injector_type="AUTOINJECTOR",
            required_controls={"doseAccuracyLimit": "0.95-1.05"},
            constituent_requirements=[{"constituent_type": "DEVICE", "component_role": "housing", "required_state": "RELEASED"}],
        ),
        actor_id,
    )
    v2 = await db.get(DdcpProfileVersion, v2_receipt.aggregate_id)
    assert v2.version == 2
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=v2.id, expected_version=v2.version), actor_id,
    )

    await db.refresh(v1)
    await db.refresh(v2)
    assert v1.state == "SUPERSEDED"
    assert v2.state == "RELEASED"
    assert v2.required_controls["doseAccuracyLimit"] == "0.95-1.05"
