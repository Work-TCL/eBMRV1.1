"""WP-08 (Document 56, SPEC-DDCP-003, INH-FR-001..030): Inhalation MDI/DPI DDCP Manufacturing Profile.
SG-150: no Document 112 schema exists for this document -- it reuses Document 54/55's tables/functions
(profile/constituent-requirement/constituent-handoff/device-assembly-record/device-functional-test-link/
release-checkpoint/evidence-manifest/ddcp_process_operation). No new tables for this document.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.modules.batch.models import Batch
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp import inhalation_commands
from app.modules.ddcp.models import (
    ConstituentHandoff,
    DdcpProcessOperation,
    DdcpProfileVersion,
    DdcpUnitBinding,
    DeviceAssemblyRecord,
    DeviceFunctionalTestLink,
    ProductionCountLedger,
)
from app.modules.equipment.models import EquipmentAsset
from app.modules.equipment.sterilization_models import ProcessCycle, ProcessCycleProfileVersion, SterilizationLoadItem
from app.modules.material.models import Material, MaterialLot
from app.modules.product.models import Product
from app.modules.product_master.models import ProductVersion
from app.modules.qms import change_commands
from app.modules.recipe.models import Recipe
from app.modules.rules import commands as rules_commands
from app.modules.signature.models import SignaturePolicy
from app.mutation.errors import (
    BlendHoldTimeExceededError,
    DoseUnitBindingAlreadyUsedError,
    FillRouteMismatchError,
    InhalationProfileNotEffectiveError,
    InhalerReconciliationFailedError,
)
from tests.conftest import idem

CLOSURE_RULE_ID = "inhalation-closure-integrity-tolerance"
CLOSURE_RULE_AST = {
    "op": "and",
    "args": [
        {"op": "gte", "args": [{"var": "value"}, "0.0"]},
        {"op": "lte", "args": [{"var": "value"}, "5.0"]},
    ],
}

HOLD_RULE_ID = "inhalation-blend-hold-time-limit"
HOLD_RULE_AST = {"op": "lte", "args": [{"var": "elapsed_hours"}, "12"]}


async def _release_rule(db, actor_id, *, rule_id, expression_ast, input_contract, seed_policy=True):
    if seed_policy:
        db.add(SignaturePolicy(record_type="rule", action="release", meaning="Released", signature_required=False))
        await db.flush()
    draft = await rules_commands.create_draft(
        db,
        rules_commands.CreateRuleDraftCommand(
            idempotency_key=idem(), rule_id=rule_id, rule_type="acceptance", semantic_version="1.0.0",
            expression_ast=expression_ast, input_contract=input_contract, output_contract={"eligible": {"type": "boolean"}},
            unit_policy={}, precision_policy={"calculation_class": "CC-5", "reported_decimal_places": 2},
            rounding_policy={"policy_version": "DOCUMENT-110-v1.0"},
        ),
        actor_id,
    )
    await rules_commands.validate_rule(db, rules_commands.ValidateRuleCommand(idempotency_key=idem(), rule_object_id=draft.aggregate_id), actor_id)
    await rules_commands.release_rule(db, rules_commands.ReleaseRuleCommand(idempotency_key=idem(), rule_object_id=draft.aggregate_id), actor_id)


async def _create_batch(db, seeded, *, batch_number: str) -> Batch:
    site_id = seeded["site_id"]
    product = Product(site_id=site_id, code=f"PROD-{batch_number}", name="Test Inhalation Product", status="active", version=1)
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
    db, seeded, *, code: str, manufacturing_profile_code: str = "inhalation_ddcp",
) -> ProductVersion:
    # SG-175: every DDCP profile now needs a real, RELEASED Product Master version
    # (`product_version_id`, migration 0089) -- "inhalation_ddcp" is Product Master's own
    # manufacturing_profile_code value for this family (Document 09), the one the command layer
    # actually checks a match against for this family (unlike Autoinjector/Coated device).
    pv = ProductVersion(
        product_business_id=f"PM-{code}", version_no=1, product_code=f"PM-{code}", name=f"Test product {code}",
        manufacturing_profile_code=manufacturing_profile_code, lifecycle_state="released", site_id=seeded["site_id"],
    )
    db.add(pv)
    await db.flush()
    return pv


async def _create_and_release_profile(db, seeded, actor_id, *, profile_code: str, subtype: str = "MDI", fill_route: str | None = "pressure_fill") -> DdcpProfileVersion:
    product_version = await _create_released_product_version(db, seeded, code=profile_code)
    receipt = await inhalation_commands.create_inhalation_profile_version(
        db,
        inhalation_commands.CreateInhalationProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=product_version.id,
            profile_code=profile_code, subtype=subtype, fill_route=fill_route,
            constituent_requirements=[
                {"constituent_type": "DRUG", "component_role": "formulation", "required_state": "RELEASED"},
                {"constituent_type": "DEVICE", "component_role": "valve", "required_state": "RELEASED"},
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
    for from_c, to_c, ref in (("DRUG", "formulation", {"batch_id": str(bulk_batch.id)}), ("DEVICE", "valve", {"lot_id": str(device_lot.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )


async def test_create_profile_and_release_requires_subtype_and_constituents(seeded, db):
    actor_id = seeded["users"]["ddcp.engineer"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INH-001", subtype="DPI", fill_route="powder_dose_fill")
    assert profile.state == "RELEASED"
    assert profile.subtype == "DPI"
    assert profile.constituent_architecture["fillRoute"] == "powder_dose_fill"


async def test_inhalation_readiness_and_start_fill_run_route_mismatch(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INH-READY", fill_route="pressure_fill")
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-READY-1")

    readiness = await inhalation_commands.evaluate_inhalation_readiness(db, batch_id=batch.id, profile_version_id=profile.id)
    assert readiness["ready"] is False

    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-FORMULATION-INH-1")
    bulk_batch.status = "released"
    device_lot = await _create_material_lot(db, seeded, code="VALVE-1", actor_id=actor_id)
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, bulk_batch, device_lot)

    readiness = await inhalation_commands.evaluate_inhalation_readiness(db, batch_id=batch.id, profile_version_id=profile.id)
    assert readiness["ready"] is True

    try:
        await inhalation_commands.start_inhaler_fill_run(
            db, inhalation_commands.StartInhalerFillRunCommand(idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, fill_route="cold_fill"), actor_id,
        )
        raised = False
    except FillRouteMismatchError:
        raised = True
    assert raised

    fill_receipt = await inhalation_commands.start_inhaler_fill_run(
        db, inhalation_commands.StartInhalerFillRunCommand(idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, fill_route="pressure_fill"), actor_id,
    )
    operation = await db.get(DdcpProcessOperation, fill_receipt.aggregate_id)
    assert operation.operation_type == "INHALER_FILL"
    assert operation.state == "EXECUTION"

    not_effective_batch = await _create_batch(db, seeded, batch_number="BATCH-INH-NOTREADY-1")
    try:
        await inhalation_commands.evaluate_inhalation_readiness(db, batch_id=not_effective_batch.id, profile_version_id=uuid.uuid4())
        raised = False
    except InhalationProfileNotEffectiveError:
        raised = True
    assert raised


async def test_blend_hold_time_exceeded_blocks_fill_start(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_rule(db, actor_id, rule_id=HOLD_RULE_ID, expression_ast=HOLD_RULE_AST, input_contract={"elapsed_hours": {"type": "decimal"}})
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INH-HOLD", fill_route="pressure_fill")
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-HOLD-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-FORMULATION-INH-2")
    bulk_batch.status = "released"
    device_lot = await _create_material_lot(db, seeded, code="VALVE-2", actor_id=actor_id)
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, bulk_batch, device_lot)

    formulation_handoff = (
        await db.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch.id, ConstituentHandoff.from_constituent == "DRUG"))
    ).scalar_one()
    formulation_handoff.accepted_at = datetime.now(timezone.utc) - timedelta(hours=48)
    await db.flush()

    try:
        await inhalation_commands.start_inhaler_fill_run(
            db,
            inhalation_commands.StartInhalerFillRunCommand(
                idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, fill_route="pressure_fill", blend_hold_limit_rule_id=HOLD_RULE_ID,
            ),
            actor_id,
        )
        raised = False
    except BlendHoldTimeExceededError:
        raised = True
    assert raised

    fill_ops = (await db.execute(select(DdcpProcessOperation).where(DdcpProcessOperation.batch_id == batch.id))).scalars().all()
    assert fill_ops == []

    formulation_handoff.accepted_at = datetime.now(timezone.utc)
    await db.flush()
    fill_receipt = await inhalation_commands.start_inhaler_fill_run(
        db,
        inhalation_commands.StartInhalerFillRunCommand(
            idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, fill_route="pressure_fill", blend_hold_limit_rule_id=HOLD_RULE_ID,
        ),
        actor_id,
    )
    operation = await db.get(DdcpProcessOperation, fill_receipt.aggregate_id)
    assert operation.state == "EXECUTION"


async def test_closure_result_dose_tests_and_complete_run(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_rule(db, actor_id, rule_id=CLOSURE_RULE_ID, expression_ast=CLOSURE_RULE_AST, input_contract={"value": {"type": "decimal"}})
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INH-CLOSE", fill_route="pressure_fill")
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-CLOSE-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-FORMULATION-INH-3")
    bulk_batch.status = "released"
    device_lot = await _create_material_lot(db, seeded, code="VALVE-3", actor_id=actor_id)
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, bulk_batch, device_lot)

    fill_receipt = await inhalation_commands.start_inhaler_fill_run(
        db, inhalation_commands.StartInhalerFillRunCommand(idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, fill_route="pressure_fill"), actor_id,
    )
    operation = await db.get(DdcpProcessOperation, fill_receipt.aggregate_id)

    closure_receipt = await inhalation_commands.record_crimp_or_closure_result(
        db, inhalation_commands.RecordCrimpOrClosureResultCommand(idempotency_key=idem(), batch_id=batch.id, unit_or_sample_id="U-1", measured_value="2.0", uom="mm", acceptance_rule_id=CLOSURE_RULE_ID), actor_id,
    )
    closure_link = await db.get(DeviceFunctionalTestLink, closure_receipt.aggregate_id)
    assert closure_link.result_state == "PASS"

    await inhalation_commands.record_inhaler_dose_test(
        db, inhalation_commands.RecordInhalerDoseTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type="DELIVERED_DOSE", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="PASS"), actor_id,
    )
    await inhalation_commands.record_dose_counter_test(
        db, inhalation_commands.RecordDoseCounterTestCommand(idempotency_key=idem(), batch_id=batch.id, unit_or_sample_id="U-1", result_state="PASS"), actor_id,
    )

    try:
        await inhalation_commands.complete_inhaler_manufacturing_run(
            db, inhalation_commands.CompleteInhalerManufacturingRunCommand(idempotency_key=idem(), operation_id=operation.id, expected_version=operation.version), actor_id,
        )
        raised = False
    except InhalerReconciliationFailedError:
        raised = True
    assert raised

    await ddcp_commands.record_syringe_unit_or_count(
        db, ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="FILLED", source="MACHINE", quantity=20), actor_id,
    )
    await inhalation_commands.complete_inhaler_manufacturing_run(
        db, inhalation_commands.CompleteInhalerManufacturingRunCommand(idempotency_key=idem(), operation_id=operation.id, expected_version=operation.version), actor_id,
    )
    await db.refresh(operation)
    assert operation.state == "COMPLETE"


async def test_release_readiness_evidence_package_and_lot_trace(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-RELEASE-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-FORMULATION-INH-4")
    bulk_batch.status = "released"
    device_lot = await _create_material_lot(db, seeded, code="VALVE-4", actor_id=actor_id)
    await db.flush()
    await _accept_constituents(db, seeded, actor_id, batch, bulk_batch, device_lot)

    readiness = await inhalation_commands.evaluate_inhaler_release_readiness(db, batch.id, actor_id)
    assert readiness["ready"] is True

    package_receipt = await inhalation_commands.create_inhaler_batch_evidence_package(
        db, inhalation_commands.CreateInhalerBatchEvidencePackageCommand(idempotency_key=idem(), batch_id=batch.id), actor_id,
    )
    assert package_receipt.resulting_version == 1

    trace = await inhalation_commands.trace_inhaler_lot(db, batch.id)
    assert trace["batch_id"] == str(batch.id)
    assert len(trace["formulation_and_component_handoffs"]) == 2


# =======================================================================================================
# Document 56 remaining gaps closed this pass: INH-FR-004/005/006/010/011/014/015/016/018/021/022/025/
# 027/028/029 (INH-FR-008 credited to the existing test_closure_result_dose_tests_and_complete_run, which
# already reconciles a FILLED production count). INH-FR-020 (cleaning/changeover), INH-FR-023 (packaging,
# blocked by SG-149) and INH-FR-030 (a negative "don't hardcode draft guidance" claim no test can honestly
# prove) stay NOT_STARTED -- not guessed.
# =======================================================================================================


async def _create_equipment_asset(db, seeded, *, code: str) -> EquipmentAsset:
    asset = EquipmentAsset(site_id=seeded["site_id"], equipment_code=code, state="QUALIFIED_AVAILABLE", qualification_status="QUALIFIED", version=1)
    db.add(asset)
    await db.flush()
    return asset


async def _create_sterilization_load_item(db, seeded, *, sterile_status: str) -> SterilizationLoadItem:
    site_id = seeded["site_id"]
    suffix = uuid.uuid4().hex[:8]
    asset = await _create_equipment_asset(db, seeded, code=f"STERI-INH-{suffix}")
    profile = ProcessCycleProfileVersion(site_id=site_id, profile_number=f"PCP-INH-{suffix}", process_type="steam_autoclave")
    db.add(profile)
    await db.flush()
    cycle = ProcessCycle(site_id=site_id, process_type="steam_autoclave", equipment_id=asset.id, profile_version_id=profile.id)
    db.add(cycle)
    await db.flush()
    item = SterilizationLoadItem(cycle_id=cycle.id, item_type="component", item_reference=f"REF-{suffix}", sterile_status=sterile_status, version=1)
    db.add(item)
    await db.flush()
    return item


async def test_propellant_and_powder_blend_constituents_captured(seeded, db):
    """INH-FR-004 (MDI propellant/excipient), INH-FR-005 (DPI powder blend) -- both modeled as DRUG-typed
    constituent_requirement component_roles, accepted via the shared constituent-handoff functions (no
    new constituent_type needed, matching Document 56's own §4 which names no distinct type for either)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    mdi_product = await _create_released_product_version(db, seeded, code="INH-MDI-PROPELLANT")

    mdi_receipt = await inhalation_commands.create_inhalation_profile_version(
        db,
        inhalation_commands.CreateInhalationProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=mdi_product.id,
            profile_code="INH-MDI-PROPELLANT", subtype="MDI", fill_route="pressure_fill",
            constituent_requirements=[
                {"constituent_type": "DRUG", "component_role": "formulation", "required_state": "RELEASED"},
                {"constituent_type": "DRUG", "component_role": "propellant", "required_state": "RELEASED"},
                {"constituent_type": "DEVICE", "component_role": "valve", "required_state": "RELEASED"},
            ],
        ),
        actor_id,
    )
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=mdi_receipt.aggregate_id, expected_version=1), actor_id,
    )
    mdi_batch = await _create_batch(db, seeded, batch_number="BATCH-INH-PROPELLANT-1")
    propellant_batch = await _create_batch(db, seeded, batch_number="BULK-PROPELLANT-1")
    propellant_batch.status = "released"
    await db.flush()
    propellant_receipt = await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=mdi_batch.id, from_constituent="DRUG", to_constituent="propellant", source_batch_reference={"batch_id": str(propellant_batch.id)}), actor_id,
    )
    await ddcp_commands.decide_constituent_handoff(
        db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=propellant_receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
    )
    propellant_handoff = await db.get(ConstituentHandoff, propellant_receipt.aggregate_id)
    assert propellant_handoff.state == "ACCEPTED"
    assert propellant_handoff.to_constituent == "propellant"

    dpi_batch = await _create_batch(db, seeded, batch_number="BATCH-INH-BLEND-1")
    blend_batch = await _create_batch(db, seeded, batch_number="BULK-POWDER-BLEND-1")
    blend_batch.status = "released"
    await db.flush()
    blend_receipt = await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=dpi_batch.id, from_constituent="DRUG", to_constituent="powder_blend", source_batch_reference={"batch_id": str(blend_batch.id)}), actor_id,
    )
    await ddcp_commands.decide_constituent_handoff(
        db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=blend_receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
    )
    blend_handoff = await db.get(ConstituentHandoff, blend_receipt.aggregate_id)
    assert blend_handoff.state == "ACCEPTED"


async def test_component_prep_verified_via_shared_sterilization_check(seeded, db):
    """INH-FR-006: 'Cleaning/handling/release of valves/canisters/actuators/blisters/capsules/device
    parts.' Reuses the exact shared decide_constituent_handoff() profile-aware sterilization check
    (PFS-FR-005's own mechanism, fully generic since Document 54's own commands.py) -- confirms an
    inhalation profile's declared STERILIZED requirement is verified the same way for a 'valve' component
    role, via Document 42's real sterilization tracking, not a guessed/unverified capture."""

    actor_id = seeded["users"]["ddcp.operator"].id
    compprep_product = await _create_released_product_version(db, seeded, code="INH-COMPPREP")
    profile_receipt = await inhalation_commands.create_inhalation_profile_version(
        db,
        inhalation_commands.CreateInhalationProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=compprep_product.id,
            profile_code="INH-COMPPREP", subtype="MDI", fill_route="pressure_fill",
            constituent_requirements=[
                {"constituent_type": "DRUG", "component_role": "formulation", "required_state": "RELEASED"},
                {"constituent_type": "DEVICE", "component_role": "valve", "required_state": "STERILIZED"},
            ],
        ),
        actor_id,
    )
    profile_id = profile_receipt.aggregate_id
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=profile_id, expected_version=1), actor_id,
    )
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-COMPPREP-1")
    valve_lot = await _create_material_lot(db, seeded, code="VALVE-COMPPREP-1", actor_id=actor_id)
    handoff_receipt = await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent="DEVICE", to_constituent="valve", source_batch_reference={"lot_id": str(valve_lot.id)}), actor_id,
    )

    load_item = await _create_sterilization_load_item(db, seeded, sterile_status="eligible")
    await ddcp_commands.decide_constituent_handoff(
        db,
        ddcp_commands.DecideConstituentHandoffCommand(
            idempotency_key=idem(), handoff_id=handoff_receipt.aggregate_id, expected_version=1, decision="ACCEPTED",
            profile_version_id=profile_id, sterilization_use_id=load_item.id,
        ),
        actor_id,
    )
    handoff = await db.get(ConstituentHandoff, handoff_receipt.aggregate_id)
    assert handoff.state == "ACCEPTED"
    assert handoff.attributes["component_prep_status_reference"]["sterile_status"] == "eligible"


async def test_device_assembly_actuator_and_dose_unit_binding_rejects_duplicate(seeded, db):
    """INH-FR-010 (device assembly with exact component lots and program -- ACTUATOR_ASSEMBLY step,
    reused from Document 54's device_assembly_record) and INH-FR-011 (DPI dose unit loading -- new
    bind_dose_unit_to_device(), rejecting a duplicate dose-unit reference)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-ASSEMBLY-1")

    assembly_receipt = await ddcp_commands.record_device_assembly_step(
        db,
        ddcp_commands.RecordDeviceAssemblyStepCommand(
            idempotency_key=idem(), batch_id=batch.id, assembly_step="ACTUATOR_ASSEMBLY", component_lot_reference={"lot_id": str(uuid.uuid4())},
        ),
        actor_id,
    )
    record = await db.get(DeviceAssemblyRecord, assembly_receipt.aggregate_id)
    assert record.assembly_step == "ACTUATOR_ASSEMBLY"

    dose_unit_ref = {"blister_id": str(uuid.uuid4())}
    binding_receipt = await inhalation_commands.bind_dose_unit_to_device(
        db, inhalation_commands.BindDoseUnitToDeviceCommand(idempotency_key=idem(), batch_id=batch.id, dose_unit_reference=dose_unit_ref, device_reference={"device_serial": "INH-DEV-1"}), actor_id,
    )
    binding = await db.get(DdcpUnitBinding, binding_receipt.aggregate_id)
    assert binding.binding_type == "DOSE_UNIT_TO_DEVICE"

    try:
        await inhalation_commands.bind_dose_unit_to_device(
            db, inhalation_commands.BindDoseUnitToDeviceCommand(idempotency_key=idem(), batch_id=batch.id, dose_unit_reference=dose_unit_ref, device_reference={"device_serial": "INH-DEV-2"}), actor_id,
        )
        raised = False
    except DoseUnitBindingAlreadyUsedError:
        raised = True
    assert raised


async def test_aerodynamic_spray_and_priming_tests_recorded(seeded, db):
    """INH-FR-014 (aerodynamic performance), INH-FR-015 (spray/plume pattern), INH-FR-016 (priming/
    repriming) -- all reuse record_inhaler_dose_test()/device_functional_test_link verbatim."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-PERF-1")

    for test_type in ("AERODYNAMIC_PARTICLE_SIZE", "SPRAY_PATTERN", "PRIMING"):
        await inhalation_commands.record_inhaler_dose_test(
            db, inhalation_commands.RecordInhalerDoseTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type=test_type, qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="PASS"), actor_id,
        )

    links = (await db.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch.id))).scalars().all()
    assert {l.test_type for l in links} == {"AERODYNAMIC_PARTICLE_SIZE", "SPRAY_PATTERN", "PRIMING"}


async def test_environment_gate_blocks_readiness_when_not_ready(seeded, db):
    """INH-FR-018: moisture/environment readiness gate. A caller-supplied environment status snapshot
    (never a baked-in humidity/temperature threshold, Document 56 §7's own 'product/validation-controlled,
    not generic constants') blocks readiness with ENVIRONMENT_NOT_READY when the profile declares an
    environment_profile_id and the snapshot reports not-ready."""

    actor_id = seeded["users"]["ddcp.operator"].id
    env_product = await _create_released_product_version(db, seeded, code="INH-ENV-1")
    profile_receipt = await inhalation_commands.create_inhalation_profile_version(
        db,
        inhalation_commands.CreateInhalationProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], product_version_id=env_product.id,
            profile_code="INH-ENV-1", subtype="DPI", fill_route="powder_dose_fill",
            environment_profile_id="ENV-DPI-STANDARD",
            constituent_requirements=[{"constituent_type": "DRUG", "component_role": "formulation", "required_state": "RELEASED"}],
        ),
        actor_id,
    )
    profile_id = profile_receipt.aggregate_id
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=profile_id, expected_version=1), actor_id,
    )
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-ENV-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-FORMULATION-ENV-1")
    bulk_batch.status = "released"
    await db.flush()
    receipt = await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent="DRUG", to_constituent="formulation", source_batch_reference={"batch_id": str(bulk_batch.id)}), actor_id,
    )
    await ddcp_commands.decide_constituent_handoff(
        db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
    )

    ready_check = await inhalation_commands.evaluate_inhalation_readiness(db, batch_id=batch.id, profile_version_id=profile_id, environment_status={"ready": True, "humidity_pct": 30})
    assert ready_check["ready"] is True

    not_ready_check = await inhalation_commands.evaluate_inhalation_readiness(db, batch_id=batch.id, profile_version_id=profile_id, environment_status={"ready": False, "humidity_pct": 75})
    assert not_ready_check["ready"] is False
    assert any(b["code"] == "ENVIRONMENT_NOT_READY" for b in not_ready_check["blockers"])


async def test_sampling_plan_and_unit_inspection_defect_captured(seeded, db):
    """INH-FR-021 (structured sampling plan -- sample_plan_reference actually populated) and INH-FR-022
    (unit/lot inspection defects -- a documented defect_code captured in qc_record_reference, same
    'logical reference, no invented taxonomy column' discipline as Document 55's INJ-FR-016)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-SAMPLE-1")

    dose_receipt = await inhalation_commands.record_inhaler_dose_test(
        db,
        inhalation_commands.RecordInhalerDoseTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="DELIVERED_DOSE", qc_record_reference={"record_id": str(uuid.uuid4())},
            method_reference={"sample_plan_reference": {"plan_id": "SP-BEGIN-MID-END", "locations": ["begin", "middle", "end"]}}, result_state="PASS",
        ),
        actor_id,
    )
    dose_link = await db.get(DeviceFunctionalTestLink, dose_receipt.aggregate_id)
    assert dose_link.method_reference["sample_plan_reference"]["locations"] == ["begin", "middle", "end"]

    inspection_receipt = await inhalation_commands.record_inhaler_dose_test(
        db,
        inhalation_commands.RecordInhalerDoseTestCommand(
            idempotency_key=idem(), batch_id=batch.id, test_type="COATING_INTEGRITY", qc_record_reference={"record_id": str(uuid.uuid4()), "defect_code": "PACK_INTEGRITY_BREACH"}, result_state="FAIL",
        ),
        actor_id,
    )
    inspection_link = await db.get(DeviceFunctionalTestLink, inspection_receipt.aggregate_id)
    assert inspection_link.qc_record_reference["defect_code"] == "PACK_INTEGRITY_BREACH"
    assert inspection_link.result_state == "FAIL"


async def test_oos_result_recorded(seeded, db):
    """INH-FR-025: 'Delivered dose/aerodynamic/device functional failures enter common OOS/OOT workflow.'
    result_state=OOS is already a real TEST_RESULT_STATES value; this confirms it round-trips."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-OOS-1")

    receipt = await inhalation_commands.record_inhaler_dose_test(
        db, inhalation_commands.RecordInhalerDoseTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type="DELIVERED_DOSE", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="OOS"), actor_id,
    )
    link = await db.get(DeviceFunctionalTestLink, receipt.aggregate_id)
    assert link.result_state == "OOS"
    assert link.blocks_release is True


async def test_release_readiness_blocks_on_pending_handoff_and_failed_test(seeded, db):
    """INH-FR-027: a real negative-path assertion -- release readiness must actually block when a device
    handoff is pending and a functional test has failed, not just the happy path."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-BLOCK-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-FORMULATION-BLOCK-1")
    bulk_batch.status = "released"
    await db.flush()

    drug_receipt = await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent="DRUG", to_constituent="formulation", source_batch_reference={"batch_id": str(bulk_batch.id)}), actor_id,
    )
    await ddcp_commands.decide_constituent_handoff(
        db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=drug_receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
    )
    # Device handoff deliberately left PENDING.
    await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent="DEVICE", to_constituent="valve", source_batch_reference={"lot_id": str(uuid.uuid4())}), actor_id,
    )
    await inhalation_commands.record_inhaler_dose_test(
        db, inhalation_commands.RecordInhalerDoseTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type="DELIVERED_DOSE", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="FAIL"), actor_id,
    )

    readiness = await inhalation_commands.evaluate_inhaler_release_readiness(db, batch.id, actor_id)
    assert readiness["ready"] is False
    assert readiness["checkpoints"]["DEVICE_CONSTITUENT"]["state"] == "BLOCKED"
    codes = {b["code"] for b in readiness["checkpoints"]["DEVICE_CONSTITUENT"]["blockers"]}
    assert "INHALER_COMPONENT_NOT_RELEASED" in codes
    assert "CLOSURE_TEST_FAILED" in codes


async def test_stability_retain_reference_and_change_linkage_reused(seeded, db):
    """INH-FR-028 (stability linkage -- reuses Document 54's record_stability_retain_reference() verbatim,
    no new code) and INH-FR-029 (change impact -- reuses get_ddcp_change_linkage() verbatim)."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-INH-STABILITY-1")

    stability_receipt = await ddcp_commands.record_stability_retain_reference(
        db, ddcp_commands.RecordStabilityRetainReferenceCommand(idempotency_key=idem(), batch_id=batch.id, plan_reference={"plan_id": "STAB-INH-1"}, quantity=4), actor_id,
    )
    stability_entry = await db.get(ProductionCountLedger, stability_receipt.aggregate_id)
    assert stability_entry.count_type == "SAMPLED"

    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="INH-CHANGE-1")
    change_receipt = await change_commands.create_change(
        db,
        change_commands.CreateChangeCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], change_number="CHG-INH-1", change_type="material",
            classification="permanent", current_state={"valve": "v1"}, proposed_state={"valve": "v2"},
            reason="Valve material change", owner_subject_id=actor_id,
        ),
        actor_id,
    )
    await change_commands.assess_impact(
        db,
        change_commands.AssessImpactCommand(
            idempotency_key=idem(), change_id=change_receipt.aggregate_id, expected_version=1,
            affected_objects=[{"object_type": "ddcp_profile_version", "object_id": str(profile.id), "impact_category": "risk", "action_required": "Re-validate valve/actuator delivery performance"}],
        ),
        actor_id,
    )
    linkage = await ddcp_commands.get_ddcp_change_linkage(db, "ddcp_profile_version", profile.id)
    assert len(linkage["changes"]) == 1
    assert linkage["changes"][0]["change_number"] == "CHG-INH-1"
