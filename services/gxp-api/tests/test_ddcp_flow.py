"""WP-08 (Document 54, SPEC-DDCP-001, PFS-FR-001..030): profile authoring/release, constituent handoff,
batch readiness, filling stage, fill IPC (rules-engine evaluated, SG-148), production counts, device
assembly independence (IND-001), functional test linking, release readiness and evidence export.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.modules.batch.models import Batch
from app.modules.ddcp import commands as ddcp_commands
from app.modules.ddcp.models import (
    ConstituentHandoff,
    DdcpProfileVersion,
    DdcpReleaseCheckpoint,
    DeviceAssemblyRecord,
    FillOperation,
    ProductionCountLedger,
)
from app.modules.equipment.cleaning_models import LineClearance
from app.modules.equipment.models import EquipmentAsset
from app.modules.equipment.sterilization_models import ProcessCycle, ProcessCycleProfileVersion, SterileFilterUse, SterilizationLoadItem
from app.modules.material.models import Material, MaterialLot
from app.modules.product.models import Product
from app.modules.recipe.models import Recipe
from app.modules.qms import change_commands
from app.modules.qms.models import DeviationRecord
from app.modules.rules import commands as rules_commands
from app.modules.signature.models import SignaturePolicy
from app.mutation.errors import (
    BulkHoldTimeExceededError,
    BulkNotReleasedError,
    ConstituentAttributeMissingError,
    ConstituentTypeMismatchError,
    DuplicateSourceEventError,
    FillStageIncompleteError,
    NotFoundError,
    PfsReconciliationFailedError,
    ProfileReleaseBlockedError,
    ReworkRouteRequiredError,
    SodConflictError,
    SterileComponentIneligibleError,
    ValidationFailedError,
)
from tests.conftest import auth_headers, idem, login

IPC_RULE_ID = "ddcp-fill-ipc-tolerance"
IPC_RULE_AST = {
    "op": "and",
    "args": [
        {"op": "gte", "args": [{"var": "value"}, "0.95"]},
        {"op": "lte", "args": [{"var": "value"}, "1.05"]},
    ],
}

# PFS-FR-007: this codebase's own SG-148 pattern (same as IPC_RULE_AST above) -- the limit lives entirely
# in this released rule, never a baseline this module invents. 24h is arbitrary test fixture data, not a
# claimed regulatory value.
HOLD_TIME_RULE_ID = "ddcp-bulk-hold-time-limit"
HOLD_TIME_RULE_AST = {"op": "lte", "args": [{"var": "elapsed_hours"}, "24"]}


async def _release_rule(db, actor_id, *, rule_id, expression_ast, input_contract, output_contract, seed_policy=True):
    # rules.release_rule() resolves record_type="rule"/action="release" -- not part of the shared
    # `seeded` fixture's signature-policy floor, so this test seeds it locally (same pattern
    # tests/test_rules.py itself uses). UniqueConstraint(record_type, action) means this must only be
    # seeded once per test -- pass seed_policy=False for a second rule released in the same test.
    if seed_policy:
        db.add(SignaturePolicy(record_type="rule", action="release", meaning="Released", signature_required=False))
        await db.flush()
    draft = await rules_commands.create_draft(
        db,
        rules_commands.CreateRuleDraftCommand(
            idempotency_key=idem(), rule_id=rule_id, rule_type="acceptance", semantic_version="1.0.0",
            expression_ast=expression_ast, input_contract=input_contract, output_contract=output_contract, unit_policy={},
            precision_policy={"calculation_class": "CC-5", "reported_decimal_places": 2},
            rounding_policy={"policy_version": "DOCUMENT-110-v1.0"},
        ),
        actor_id,
    )
    await rules_commands.validate_rule(db, rules_commands.ValidateRuleCommand(idempotency_key=idem(), rule_object_id=draft.aggregate_id), actor_id)
    await rules_commands.release_rule(db, rules_commands.ReleaseRuleCommand(idempotency_key=idem(), rule_object_id=draft.aggregate_id), actor_id)


async def _release_ipc_rule(db, actor_id):
    await _release_rule(
        db, actor_id, rule_id=IPC_RULE_ID, expression_ast=IPC_RULE_AST,
        input_contract={"value": {"type": "decimal"}}, output_contract={"eligible": {"type": "boolean"}},
    )


async def _release_hold_time_rule(db, actor_id):
    await _release_rule(
        db, actor_id, rule_id=HOLD_TIME_RULE_ID, expression_ast=HOLD_TIME_RULE_AST,
        input_contract={"elapsed_hours": {"type": "decimal"}}, output_contract={"eligible": {"type": "boolean"}},
    )


async def _create_sterilization_load_item(db, seeded, *, sterile_status: str) -> SterilizationLoadItem:
    site_id = seeded["site_id"]
    suffix = uuid.uuid4().hex[:8]
    asset = await _create_equipment_asset(db, seeded, code=f"STERI-{suffix}")
    profile = ProcessCycleProfileVersion(site_id=site_id, profile_number=f"PCP-{suffix}", process_type="steam_autoclave")
    db.add(profile)
    await db.flush()
    cycle = ProcessCycle(site_id=site_id, process_type="steam_autoclave", equipment_id=asset.id, profile_version_id=profile.id)
    db.add(cycle)
    await db.flush()
    item = SterilizationLoadItem(cycle_id=cycle.id, item_type="component", item_reference=f"REF-{suffix}", sterile_status=sterile_status, version=1)
    db.add(item)
    await db.flush()
    return item


async def _create_batch(db, seeded, *, batch_number: str) -> Batch:
    site_id = seeded["site_id"]
    product = Product(site_id=site_id, code=f"PROD-{batch_number}", name="Test Injectable Product", status="active", version=1)
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


async def _create_equipment_asset(db, seeded, *, code: str) -> EquipmentAsset:
    asset = EquipmentAsset(
        site_id=seeded["site_id"], equipment_code=code, state="QUALIFIED_AVAILABLE",
        qualification_status="QUALIFIED", version=1,
    )
    db.add(asset)
    await db.flush()
    return asset


async def _clear_line(db, seeded, area_id):
    db.add(LineClearance(site_id=seeded["site_id"], area_id=area_id, state="CLEARED", version=1))
    await db.flush()


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
    receipt = await ddcp_commands.create_injectable_profile_version(
        db,
        ddcp_commands.CreateInjectableProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], profile_code=profile_code, subtype="PREFILLED_SYRINGE",
            constituent_architecture={"drug": "biologic"}, required_controls={"sterileProcess": {"aseptic": True}},
            constituent_requirements=[
                {"constituent_type": "DRUG", "component_role": "bulk_drug", "required_state": "RELEASED"},
                {"constituent_type": "DEVICE", "component_role": "barrel", "required_state": "RELEASED"},
            ],
        ),
        actor_id,
    )
    profile_id = receipt.aggregate_id
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=profile_id, expected_version=1), actor_id,
    )
    return await db.get(DdcpProfileVersion, profile_id)


async def test_create_profile_and_release_requires_constituent_requirements(seeded, db):
    actor_id = seeded["users"]["ddcp.engineer"].id
    empty = await ddcp_commands.create_injectable_profile_version(
        db,
        ddcp_commands.CreateInjectableProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], profile_code="PFS-EMPTY",
            constituent_architecture={}, required_controls={},
        ),
        actor_id,
    )
    try:
        await ddcp_commands.release_injectable_profile_version(
            db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=empty.aggregate_id, expected_version=1), actor_id,
        )
        raised = False
    except ProfileReleaseBlockedError:
        raised = True
    assert raised

    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-001")
    assert profile.state == "RELEASED"
    assert profile.effective_from is not None


async def test_constituent_handoff_requires_released_source_then_accepts(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-HANDOFF-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-1")
    bulk_batch.status = "planned"  # not released yet
    await db.flush()

    handoff_receipt = await ddcp_commands.record_constituent_handoff(
        db,
        ddcp_commands.RecordConstituentHandoffCommand(
            idempotency_key=idem(), batch_id=batch.id, from_constituent="DRUG", to_constituent="bulk_drug",
            source_batch_reference={"batch_id": str(bulk_batch.id)},
        ),
        actor_id,
    )

    try:
        await ddcp_commands.decide_constituent_handoff(
            db,
            ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=handoff_receipt.aggregate_id, expected_version=1, decision="ACCEPTED"),
            actor_id,
        )
        raised = False
    except BulkNotReleasedError:
        raised = True
    assert raised

    bulk_batch.status = "released"
    await db.flush()
    await ddcp_commands.decide_constituent_handoff(
        db,
        ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=handoff_receipt.aggregate_id, expected_version=1, decision="ACCEPTED"),
        actor_id,
    )
    handoff = await db.get(ConstituentHandoff, handoff_receipt.aggregate_id)
    assert handoff.state == "ACCEPTED"


async def test_readiness_blocks_on_missing_handoff_and_passes_once_satisfied(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-READY")
    batch = await _create_batch(db, seeded, batch_number="BATCH-READY-1")

    readiness = await ddcp_commands.evaluate_injectable_batch_readiness(db, batch_id=batch.id, profile_version_id=profile.id)
    assert readiness["ready"] is False
    codes = {b["code"] for b in readiness["blockers"]}
    assert "BULK_NOT_RELEASED" in codes and "PRIMARY_COMPONENT_NOT_RELEASED" in codes

    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-2")
    bulk_batch.status = "released"
    lot = await _create_material_lot(db, seeded, code="BARREL-1", actor_id=actor_id)
    await db.flush()
    for from_c, to_c, ref in (("DRUG", "bulk_drug", {"batch_id": str(bulk_batch.id)}), ("DEVICE", "barrel", {"lot_id": str(lot.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )

    readiness = await ddcp_commands.evaluate_injectable_batch_readiness(db, batch_id=batch.id, profile_version_id=profile.id)
    assert readiness["ready"] is True


async def test_start_filling_stage_and_fill_ipc_oos_holds_operation(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_ipc_rule(db, actor_id)
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-FILL")
    batch = await _create_batch(db, seeded, batch_number="BATCH-FILL-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-3")
    bulk_batch.status = "released"
    lot = await _create_material_lot(db, seeded, code="BARREL-2", actor_id=actor_id)
    area = seeded["areas"]["AREA-GRADE-A"]
    await _clear_line(db, seeded, area.id)
    asset = await _create_equipment_asset(db, seeded, code="FILLER-1")
    await db.flush()
    for from_c, to_c, ref in (("DRUG", "bulk_drug", {"batch_id": str(bulk_batch.id)}), ("DEVICE", "barrel", {"lot_id": str(lot.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )

    fill_receipt = await ddcp_commands.start_filling_stage(
        db,
        ddcp_commands.StartFillingStageCommand(
            idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, line_id=area.id,
            filler_equipment_id=asset.id, fill_program_id="PROG-1", fill_program_version="v1",
            product_contact_path={"path": "single-use"}, target_fill="1.0", target_fill_uom="mL",
        ),
        actor_id,
    )
    fill_op = await db.get(FillOperation, fill_receipt.aggregate_id)
    assert fill_op.state == "EXECUTION"

    await ddcp_commands.record_fill_ipc_result(
        db,
        ddcp_commands.RecordFillIpcResultCommand(
            idempotency_key=idem(), fill_operation_id=fill_op.id, expected_version=fill_op.version, sample_id="S-1",
            actual_value="0.5", uom="mL", source="MANUAL", acceptance_rule_id=IPC_RULE_ID,
        ),
        actor_id,
    )
    await db.refresh(fill_op)
    assert fill_op.state == "HOLD"
    assert fill_op.requires_deviation is True

    try:
        await ddcp_commands.complete_filling_stage(
            db, ddcp_commands.CompleteFillingStageCommand(idempotency_key=idem(), fill_operation_id=fill_op.id, expected_version=fill_op.version), actor_id,
        )
        raised = False
    except FillStageIncompleteError:
        raised = True
    assert raised


async def test_syringe_count_duplicate_source_event_rejected(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-COUNT-1")

    await ddcp_commands.record_syringe_unit_or_count(
        db,
        ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="FILLED", source="MACHINE", quantity=50, source_event_id="EVT-1"),
        actor_id,
    )
    try:
        await ddcp_commands.record_syringe_unit_or_count(
            db,
            ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="FILLED", source="MACHINE", quantity=50, source_event_id="EVT-1"),
            actor_id,
        )
        raised = False
    except DuplicateSourceEventError:
        raised = True
    assert raised


async def test_complete_filling_stage_requires_filled_units_recorded(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-COMPLETE")
    batch = await _create_batch(db, seeded, batch_number="BATCH-COMPLETE-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-4")
    bulk_batch.status = "released"
    lot = await _create_material_lot(db, seeded, code="BARREL-3", actor_id=actor_id)
    area = seeded["areas"]["AREA-GRADE-C"]
    await _clear_line(db, seeded, area.id)
    asset = await _create_equipment_asset(db, seeded, code="FILLER-2")
    await db.flush()
    for from_c, to_c, ref in (("DRUG", "bulk_drug", {"batch_id": str(bulk_batch.id)}), ("DEVICE", "barrel", {"lot_id": str(lot.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )
    fill_receipt = await ddcp_commands.start_filling_stage(
        db,
        ddcp_commands.StartFillingStageCommand(
            idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, line_id=area.id,
            filler_equipment_id=asset.id, fill_program_id="PROG-2", fill_program_version="v1",
            product_contact_path={"path": "single-use"}, target_fill="1.0", target_fill_uom="mL",
        ),
        actor_id,
    )
    fill_op = await db.get(FillOperation, fill_receipt.aggregate_id)

    try:
        await ddcp_commands.complete_filling_stage(
            db, ddcp_commands.CompleteFillingStageCommand(idempotency_key=idem(), fill_operation_id=fill_op.id, expected_version=fill_op.version), actor_id,
        )
        raised = False
    except PfsReconciliationFailedError:
        raised = True
    assert raised

    await ddcp_commands.record_syringe_unit_or_count(
        db, ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="FILLED", source="MACHINE", quantity=900), actor_id,
    )
    await ddcp_commands.complete_filling_stage(
        db, ddcp_commands.CompleteFillingStageCommand(idempotency_key=idem(), fill_operation_id=fill_op.id, expected_version=fill_op.version), actor_id,
    )
    await db.refresh(fill_op)
    assert fill_op.state == "COMPLETE"


async def test_device_assembly_requires_independent_verifier(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    other_actor_id = seeded["users"]["operator1"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-ASSEMBLY-1")

    receipt = await ddcp_commands.record_device_assembly_step(
        db,
        ddcp_commands.RecordDeviceAssemblyStepCommand(
            idempotency_key=idem(), batch_id=batch.id, assembly_step="NEEDLE_INSTALL", component_lot_reference={"lot_id": str(uuid.uuid4())},
        ),
        actor_id,
    )

    try:
        await ddcp_commands.verify_device_assembly_step(
            db, ddcp_commands.VerifyDeviceAssemblyStepCommand(idempotency_key=idem(), record_id=receipt.aggregate_id, expected_version=1), actor_id,
        )
        raised = False
    except SodConflictError:
        raised = True
    assert raised

    await ddcp_commands.verify_device_assembly_step(
        db, ddcp_commands.VerifyDeviceAssemblyStepCommand(idempotency_key=idem(), record_id=receipt.aggregate_id, expected_version=1), other_actor_id,
    )
    record = await db.get(DeviceAssemblyRecord, receipt.aggregate_id)
    assert record.verified_by == other_actor_id


async def test_functional_test_and_release_readiness_and_evidence_package(seeded, db):
    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-RELEASE-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-5")
    bulk_batch.status = "released"
    await db.flush()
    handoff_receipt = await ddcp_commands.record_constituent_handoff(
        db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent="DRUG", to_constituent="bulk_drug", source_batch_reference={"batch_id": str(bulk_batch.id)}), actor_id,
    )
    await ddcp_commands.decide_constituent_handoff(
        db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=handoff_receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
    )

    await ddcp_commands.record_pfs_functional_test(
        db,
        ddcp_commands.RecordPfsFunctionalTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type="CCI", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="FAIL"),
        actor_id,
    )

    readiness = await ddcp_commands.evaluate_pfs_release_readiness(db, batch.id, actor_id)
    assert readiness["ready"] is False
    assert readiness["checkpoints"]["DEVICE_CONSTITUENT"]["state"] == "BLOCKED"

    await ddcp_commands.record_syringe_unit_or_count(
        db, ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="FILLED", source="MACHINE", quantity=10), actor_id,
    )
    await ddcp_commands.record_pfs_functional_test(
        db,
        ddcp_commands.RecordPfsFunctionalTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type="CCI", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="PASS"),
        actor_id,
    )
    readiness = await ddcp_commands.evaluate_pfs_release_readiness(db, batch.id, actor_id)
    assert readiness["ready"] is True

    checkpoints = (await db.execute(select(DdcpReleaseCheckpoint).where(DdcpReleaseCheckpoint.batch_id == batch.id))).scalars().all()
    assert len(checkpoints) == 3

    package_receipt = await ddcp_commands.create_pfs_batch_evidence_package(
        db, ddcp_commands.CreatePfsBatchEvidencePackageCommand(idempotency_key=idem(), batch_id=batch.id), actor_id,
    )
    assert package_receipt.resulting_version == 1


async def test_create_profile_via_api_requires_permission(client, seeded):
    token = await login(client, "operator1")
    resp = await client.post(
        "/ddcp/v1/prefilled-syringe/profiles",
        json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "profile_code": "PFS-API-1", "constituent_architecture": {}, "required_controls": {}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text

    token = await login(client, "ddcp.engineer")
    resp = await client.post(
        "/ddcp/v1/prefilled-syringe/profiles",
        json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "profile_code": "PFS-API-2", "constituent_architecture": {}, "required_controls": {}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_batch_genealogy_not_found_for_unknown_batch(seeded, db):
    try:
        await ddcp_commands.get_pfs_batch_genealogy(db, uuid.uuid4())
        raised = False
    except NotFoundError:
        raised = True
    assert raised


async def test_batch_genealogy_and_review_summary_compose_cross_module_evidence(seeded, db):
    """PFS-FR-021/025: both are pure read compositions -- this test asserts they surface the exception
    signals a reviewer needs (open hold, IPC OOS, failed device assembly/test, open deviation) without
    either function performing a single write of its own."""

    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_ipc_rule(db, actor_id)
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-REVIEW")
    batch = await _create_batch(db, seeded, batch_number="BATCH-REVIEW-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-REVIEW")
    bulk_batch.status = "released"
    lot = await _create_material_lot(db, seeded, code="BARREL-REVIEW", actor_id=actor_id)
    area = seeded["areas"]["AREA-GRADE-A"]
    await _clear_line(db, seeded, area.id)
    asset = await _create_equipment_asset(db, seeded, code="FILLER-REVIEW")
    await db.flush()

    for from_c, to_c, ref in (("DRUG", "bulk_drug", {"batch_id": str(bulk_batch.id)}), ("DEVICE", "barrel", {"lot_id": str(lot.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )

    fill_receipt = await ddcp_commands.start_filling_stage(
        db,
        ddcp_commands.StartFillingStageCommand(
            idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, line_id=area.id,
            filler_equipment_id=asset.id, fill_program_id="PROG-REVIEW", fill_program_version="v1",
            product_contact_path={"path": "single-use"}, target_fill="1.0", target_fill_uom="mL",
        ),
        actor_id,
    )
    fill_op = await db.get(FillOperation, fill_receipt.aggregate_id)

    await ddcp_commands.record_aseptic_intervention_for_fill(
        db,
        ddcp_commands.RecordAsepticInterventionForFillCommand(
            idempotency_key=idem(), fill_operation_id=fill_op.id, expected_version=fill_op.version, intervention_type="LINE_STOPPAGE",
            started_at=datetime.now(timezone.utc),
        ),
        actor_id,
    )
    await db.refresh(fill_op)

    await ddcp_commands.record_fill_ipc_result(
        db,
        ddcp_commands.RecordFillIpcResultCommand(
            idempotency_key=idem(), fill_operation_id=fill_op.id, expected_version=fill_op.version, sample_id="S-REVIEW",
            actual_value="0.5", uom="mL", source="MANUAL", acceptance_rule_id=IPC_RULE_ID,
        ),
        actor_id,
    )
    await db.refresh(fill_op)
    assert fill_op.state == "HOLD"  # OOS result -- exercises the fill_operations_on_hold/fill_ipc_oos_count signals

    await ddcp_commands.record_syringe_unit_or_count(
        db, ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="FILLED", source="MACHINE", quantity=8), actor_id,
    )
    await ddcp_commands.record_syringe_unit_or_count(
        db, ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="REJECTED_VISUAL", source="MANUAL", quantity=2), actor_id,
    )

    await ddcp_commands.record_device_assembly_step(
        db,
        ddcp_commands.RecordDeviceAssemblyStepCommand(
            idempotency_key=idem(), batch_id=batch.id, assembly_step="NEEDLE_INSTALL", component_lot_reference={"lot_id": str(uuid.uuid4())},
            unit_identifier="UNIT-1", result="FAIL",
        ),
        actor_id,
    )
    await ddcp_commands.record_pfs_functional_test(
        db,
        ddcp_commands.RecordPfsFunctionalTestCommand(idempotency_key=idem(), batch_id=batch.id, test_type="CCI", qc_record_reference={"record_id": str(uuid.uuid4())}, result_state="FAIL"),
        actor_id,
    )

    db.add(DeviationRecord(
        site_id=seeded["site_id"], deviation_number="DEV-REVIEW-1", deviation_type="process", source_type="batch",
        source_id=batch.id, severity="major", owner_subject_id=actor_id, state="OPEN",
    ))
    # A deviation opened elsewhere that also names this batch via cross_batch_ids -- exercises the JSONB
    # containment match, not just the direct source_type='batch' match.
    other_batch = await _create_batch(db, seeded, batch_number="BATCH-REVIEW-OTHER")
    db.add(DeviationRecord(
        site_id=seeded["site_id"], deviation_number="DEV-REVIEW-2", deviation_type="process", source_type="batch",
        source_id=other_batch.id, severity="minor", owner_subject_id=actor_id, state="OPEN",
        cross_batch_ids=[str(batch.id)],
    ))
    await db.flush()

    genealogy = await ddcp_commands.get_pfs_batch_genealogy(db, batch.id)
    assert genealogy["batch_id"] == str(batch.id)
    assert {h["to_constituent"] for h in genealogy["incoming_constituents"]} == {"bulk_drug", "barrel"}
    assert genealogy["device_assembly_chain"][0]["unit_identifier"] == "UNIT-1"
    assert {c["count_type"] for c in genealogy["production_counts"]} == {"FILLED", "REJECTED_VISUAL"}
    assert genealogy["functional_test_links"][0]["result_state"] == "FAIL"

    summary = await ddcp_commands.get_pfs_batch_review_summary(db, batch.id)
    assert summary["batch_id"] == str(batch.id)
    exceptions = summary["exception_summary"]
    assert exceptions["fill_operations_on_hold"] == 1
    assert exceptions["fill_ipc_oos_count"] == 1
    assert exceptions["device_assembly_exceptions"] == 1
    assert exceptions["device_test_exceptions"] == 1
    assert exceptions["open_deviations"] == 2
    assert len(summary["aseptic_timeline"]) == 1
    assert summary["defect_counts"] == {"FILLED": 8, "REJECTED_VISUAL": 2}
    assert {d["deviation_number"] for d in summary["deviations"]} == {"DEV-REVIEW-1", "DEV-REVIEW-2"}
    assert summary["genealogy"]["batch_id"] == str(batch.id)


# =======================================================================================================
# Document 54 remaining gaps, closed this pass: PFS-FR-005/007/008/016/019/026/027/028/029.
# PFS-FR-020 (label/packaging) stays NOT_STARTED -- SG-149 (ebmr.batches vs ebmr.gxp_batch divergence).
# =======================================================================================================


async def test_decide_handoff_profile_aware_checks_type_prep_and_attributes(seeded, db):
    """PFS-FR-005 (component preparation, verified via Document 42's real sterilization tracking),
    PFS-FR-016 (declared attribute presence) and PFS-FR-028 (no implicit constituent_type equivalency),
    all gated behind the new optional `profile_version_id` on DecideConstituentHandoffCommand."""

    actor_id = seeded["users"]["ddcp.operator"].id
    site_id = seeded["site_id"]

    profile_receipt = await ddcp_commands.create_injectable_profile_version(
        db,
        ddcp_commands.CreateInjectableProfileVersionCommand(
            idempotency_key=idem(), site_id=site_id, profile_code="PFS-PROFILE-AWARE", subtype="PREFILLED_SYRINGE",
            constituent_architecture={}, required_controls={},
            constituent_requirements=[
                {"constituent_type": "DRUG", "component_role": "bulk_drug", "required_state": "RELEASED"},
                {"constituent_type": "DEVICE", "component_role": "stopper", "required_state": "STERILIZED"},
                {
                    "constituent_type": "DEVICE", "component_role": "needle", "required_state": "RELEASED",
                    "attribute_requirements": {"silicone_level": {"unit": "ug"}},
                },
            ],
        ),
        actor_id,
    )
    profile_id = profile_receipt.aggregate_id
    await ddcp_commands.release_injectable_profile_version(
        db, ddcp_commands.ReleaseInjectableProfileVersionCommand(idempotency_key=idem(), profile_id=profile_id, expected_version=1), actor_id,
    )
    batch = await _create_batch(db, seeded, batch_number="BATCH-PROFILE-AWARE-1")

    # PFS-FR-028: a BIOLOGIC handoff against a requirement declared DRUG -- no implicit equivalency.
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-AWARE-1")
    bulk_batch.status = "released"
    await db.flush()
    mismatch_receipt = await ddcp_commands.record_constituent_handoff(
        db,
        ddcp_commands.RecordConstituentHandoffCommand(
            idempotency_key=idem(), batch_id=batch.id, from_constituent="BIOLOGIC", to_constituent="bulk_drug",
            source_batch_reference={"batch_id": str(bulk_batch.id)},
        ),
        actor_id,
    )
    try:
        await ddcp_commands.decide_constituent_handoff(
            db,
            ddcp_commands.DecideConstituentHandoffCommand(
                idempotency_key=idem(), handoff_id=mismatch_receipt.aggregate_id, expected_version=1, decision="ACCEPTED",
                profile_version_id=profile_id,
            ),
            actor_id,
        )
        raised = False
    except ConstituentTypeMismatchError:
        raised = True
    assert raised

    # PFS-FR-005: profile requires STERILIZED for "stopper" -- no reference, then a not-ready reference,
    # then a ready reference, verified against Document 42's real sterilization tracking each time.
    stopper_lot = await _create_material_lot(db, seeded, code="STOPPER-AWARE-1", actor_id=actor_id)
    stopper_receipt = await ddcp_commands.record_constituent_handoff(
        db,
        ddcp_commands.RecordConstituentHandoffCommand(
            idempotency_key=idem(), batch_id=batch.id, from_constituent="DEVICE", to_constituent="stopper",
            source_batch_reference={"lot_id": str(stopper_lot.id)},
        ),
        actor_id,
    )
    try:
        await ddcp_commands.decide_constituent_handoff(
            db,
            ddcp_commands.DecideConstituentHandoffCommand(
                idempotency_key=idem(), handoff_id=stopper_receipt.aggregate_id, expected_version=1, decision="ACCEPTED",
                profile_version_id=profile_id,
            ),
            actor_id,
        )
        raised = False
    except SterileComponentIneligibleError:
        raised = True
    assert raised

    load_item_not_ready = await _create_sterilization_load_item(db, seeded, sterile_status="pending")
    try:
        await ddcp_commands.decide_constituent_handoff(
            db,
            ddcp_commands.DecideConstituentHandoffCommand(
                idempotency_key=idem(), handoff_id=stopper_receipt.aggregate_id, expected_version=1, decision="ACCEPTED",
                profile_version_id=profile_id, sterilization_use_id=load_item_not_ready.id,
            ),
            actor_id,
        )
        raised = False
    except SterileComponentIneligibleError:
        raised = True
    assert raised

    load_item_ready = await _create_sterilization_load_item(db, seeded, sterile_status="eligible")
    await ddcp_commands.decide_constituent_handoff(
        db,
        ddcp_commands.DecideConstituentHandoffCommand(
            idempotency_key=idem(), handoff_id=stopper_receipt.aggregate_id, expected_version=1, decision="ACCEPTED",
            profile_version_id=profile_id, sterilization_use_id=load_item_ready.id,
        ),
        actor_id,
    )
    stopper_handoff = await db.get(ConstituentHandoff, stopper_receipt.aggregate_id)
    assert stopper_handoff.state == "ACCEPTED"
    assert stopper_handoff.attributes["component_prep_status_reference"]["sterile_status"] == "eligible"

    # PFS-FR-016: profile declares attribute_requirements for "needle" -- missing key rejected, present accepted.
    needle_lot_1 = await _create_material_lot(db, seeded, code="NEEDLE-AWARE-1", actor_id=actor_id)
    needle_receipt_1 = await ddcp_commands.record_constituent_handoff(
        db,
        ddcp_commands.RecordConstituentHandoffCommand(
            idempotency_key=idem(), batch_id=batch.id, from_constituent="DEVICE", to_constituent="needle",
            source_batch_reference={"lot_id": str(needle_lot_1.id)},
        ),
        actor_id,
    )
    try:
        await ddcp_commands.decide_constituent_handoff(
            db,
            ddcp_commands.DecideConstituentHandoffCommand(
                idempotency_key=idem(), handoff_id=needle_receipt_1.aggregate_id, expected_version=1, decision="ACCEPTED",
                profile_version_id=profile_id,
            ),
            actor_id,
        )
        raised = False
    except ConstituentAttributeMissingError:
        raised = True
    assert raised

    needle_lot_2 = await _create_material_lot(db, seeded, code="NEEDLE-AWARE-2", actor_id=actor_id)
    needle_receipt_2 = await ddcp_commands.record_constituent_handoff(
        db,
        ddcp_commands.RecordConstituentHandoffCommand(
            idempotency_key=idem(), batch_id=batch.id, from_constituent="DEVICE", to_constituent="needle",
            source_batch_reference={"lot_id": str(needle_lot_2.id)}, attributes={"silicone_level": "12.5ug"},
        ),
        actor_id,
    )
    await ddcp_commands.decide_constituent_handoff(
        db,
        ddcp_commands.DecideConstituentHandoffCommand(
            idempotency_key=idem(), handoff_id=needle_receipt_2.aggregate_id, expected_version=1, decision="ACCEPTED",
            profile_version_id=profile_id,
        ),
        actor_id,
    )
    needle_handoff = await db.get(ConstituentHandoff, needle_receipt_2.aggregate_id)
    assert needle_handoff.state == "ACCEPTED"


async def test_start_filling_stage_bulk_hold_time_exceeded_blocks(seeded, db):
    """PFS-FR-007: caller-supplied released rule (SG-148 pattern), never an invented limit."""

    actor_id = seeded["users"]["ddcp.operator"].id
    await _release_hold_time_rule(db, actor_id)
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-HOLD")
    batch = await _create_batch(db, seeded, batch_number="BATCH-HOLD-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-HOLD")
    bulk_batch.status = "released"
    lot = await _create_material_lot(db, seeded, code="BARREL-HOLD", actor_id=actor_id)
    area = seeded["areas"]["AREA-GRADE-A"]
    await _clear_line(db, seeded, area.id)
    asset = await _create_equipment_asset(db, seeded, code="FILLER-HOLD")
    await db.flush()

    handoff_ids = {}
    for from_c, to_c, ref in (("DRUG", "bulk_drug", {"batch_id": str(bulk_batch.id)}), ("DEVICE", "barrel", {"lot_id": str(lot.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )
        handoff_ids[from_c] = receipt.aggregate_id

    bulk_handoff = await db.get(ConstituentHandoff, handoff_ids["DRUG"])
    bulk_handoff.accepted_at = datetime.now(timezone.utc) - timedelta(hours=100)
    await db.flush()

    try:
        await ddcp_commands.start_filling_stage(
            db,
            ddcp_commands.StartFillingStageCommand(
                idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, line_id=area.id,
                filler_equipment_id=asset.id, fill_program_id="PROG-HOLD-1", fill_program_version="v1",
                product_contact_path={"path": "single-use"}, target_fill="1.0", target_fill_uom="mL",
                bulk_hold_limit_rule_id=HOLD_TIME_RULE_ID,
            ),
            actor_id,
        )
        raised = False
    except BulkHoldTimeExceededError:
        raised = True
    assert raised

    fill_ops = (await db.execute(select(FillOperation).where(FillOperation.batch_id == batch.id))).scalars().all()
    assert fill_ops == []  # no partial FillOperation row committed by the blocked attempt

    bulk_handoff.accepted_at = datetime.now(timezone.utc)
    await db.flush()
    fill_receipt = await ddcp_commands.start_filling_stage(
        db,
        ddcp_commands.StartFillingStageCommand(
            idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, line_id=area.id,
            filler_equipment_id=asset.id, fill_program_id="PROG-HOLD-2", fill_program_version="v1",
            product_contact_path={"path": "single-use"}, target_fill="1.0", target_fill_uom="mL",
            bulk_hold_limit_rule_id=HOLD_TIME_RULE_ID,
        ),
        actor_id,
    )
    fill_op = await db.get(FillOperation, fill_receipt.aggregate_id)
    assert fill_op.state == "EXECUTION"


async def test_complete_filling_stage_binds_filter_use_id(seeded, db):
    """PFS-FR-008: bind, not just check -- the reference is now persisted onto FillOperation."""

    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-FILTER")
    batch = await _create_batch(db, seeded, batch_number="BATCH-FILTER-1")
    bulk_batch = await _create_batch(db, seeded, batch_number="BULK-DRUG-FILTER-1")
    bulk_batch.status = "released"
    lot = await _create_material_lot(db, seeded, code="BARREL-FILTER-1", actor_id=actor_id)
    area = seeded["areas"]["AREA-GRADE-A"]
    await _clear_line(db, seeded, area.id)
    asset = await _create_equipment_asset(db, seeded, code="FILLER-FILTER-1")
    filter_use = SterileFilterUse(site_id=seeded["site_id"], filter_serial="FILTER-SN-1", state="RECEIVED_ELIGIBLE")
    db.add(filter_use)
    await db.flush()

    for from_c, to_c, ref in (("DRUG", "bulk_drug", {"batch_id": str(bulk_batch.id)}), ("DEVICE", "barrel", {"lot_id": str(lot.id)})):
        receipt = await ddcp_commands.record_constituent_handoff(
            db, ddcp_commands.RecordConstituentHandoffCommand(idempotency_key=idem(), batch_id=batch.id, from_constituent=from_c, to_constituent=to_c, source_batch_reference=ref), actor_id,
        )
        await ddcp_commands.decide_constituent_handoff(
            db, ddcp_commands.DecideConstituentHandoffCommand(idempotency_key=idem(), handoff_id=receipt.aggregate_id, expected_version=1, decision="ACCEPTED"), actor_id,
        )

    fill_receipt = await ddcp_commands.start_filling_stage(
        db,
        ddcp_commands.StartFillingStageCommand(
            idempotency_key=idem(), batch_id=batch.id, profile_version_id=profile.id, line_id=area.id,
            filler_equipment_id=asset.id, fill_program_id="PROG-FILTER-1", fill_program_version="v1",
            product_contact_path={"path": "single-use"}, target_fill="1.0", target_fill_uom="mL",
        ),
        actor_id,
    )
    fill_op = await db.get(FillOperation, fill_receipt.aggregate_id)
    await ddcp_commands.record_syringe_unit_or_count(
        db, ddcp_commands.RecordSyringeUnitOrCountCommand(idempotency_key=idem(), batch_id=batch.id, count_type="FILLED", source="MACHINE", quantity=5), actor_id,
    )
    await ddcp_commands.complete_filling_stage(
        db,
        ddcp_commands.CompleteFillingStageCommand(idempotency_key=idem(), fill_operation_id=fill_op.id, expected_version=fill_op.version, filter_use_id=filter_use.id),
        actor_id,
    )
    await db.refresh(fill_op)
    assert fill_op.filter_use_id == filter_use.id
    assert fill_op.state == "COMPLETE"


async def test_record_device_assembly_step_rework_requires_procedure_reference(seeded, db):
    """PFS-FR-027: default disallowed unless a released-procedure reference is explicitly supplied."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-REWORK-1")

    try:
        await ddcp_commands.record_device_assembly_step(
            db,
            ddcp_commands.RecordDeviceAssemblyStepCommand(
                idempotency_key=idem(), batch_id=batch.id, assembly_step="NEEDLE_INSTALL",
                component_lot_reference={"lot_id": str(uuid.uuid4())}, result="REWORK",
            ),
            actor_id,
        )
        raised = False
    except ReworkRouteRequiredError:
        raised = True
    assert raised

    receipt = await ddcp_commands.record_device_assembly_step(
        db,
        ddcp_commands.RecordDeviceAssemblyStepCommand(
            idempotency_key=idem(), batch_id=batch.id, assembly_step="NEEDLE_INSTALL",
            component_lot_reference={"lot_id": str(uuid.uuid4())}, result="REWORK",
            rework_procedure_reference={"procedure_id": "SOP-REWORK-1", "version": 2},
        ),
        actor_id,
    )
    record = await db.get(DeviceAssemblyRecord, receipt.aggregate_id)
    assert record.result == "REWORK"
    assert record.process_parameters["rework_procedure_reference"]["procedure_id"] == "SOP-REWORK-1"


async def test_record_stability_retain_reference(seeded, db):
    """PFS-FR-026: no dedicated stability/retain-plan entity exists -- reuses production_count_ledger's
    own SAMPLED count_type, carrying the plan reference as a logical JSONB reference."""

    actor_id = seeded["users"]["ddcp.operator"].id
    batch = await _create_batch(db, seeded, batch_number="BATCH-RETAIN-1")

    receipt = await ddcp_commands.record_stability_retain_reference(
        db,
        ddcp_commands.RecordStabilityRetainReferenceCommand(
            idempotency_key=idem(), batch_id=batch.id, plan_reference={"plan_id": "STAB-PLAN-1", "protocol": "PR-100"}, quantity=6,
        ),
        actor_id,
    )
    entry = await db.get(ProductionCountLedger, receipt.aggregate_id)
    assert entry.count_type == "SAMPLED"
    assert entry.quantity == 6
    assert entry.device_reference["stability_retain_plan_reference"]["plan_id"] == "STAB-PLAN-1"


async def test_verify_pfs_serialization_compliance(seeded, db):
    """PFS-FR-019: presence-only check, gated by the profile's own declared serialization requirement --
    never a UDI format guess."""

    actor_id = seeded["users"]["ddcp.operator"].id
    profile_receipt = await ddcp_commands.create_injectable_profile_version(
        db,
        ddcp_commands.CreateInjectableProfileVersionCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], profile_code="PFS-SERIAL",
            constituent_architecture={}, required_controls={"serialization": {"required": True}},
        ),
        actor_id,
    )
    profile_id = profile_receipt.aggregate_id
    batch = await _create_batch(db, seeded, batch_number="BATCH-SERIAL-1")

    await ddcp_commands.record_device_assembly_step(
        db,
        ddcp_commands.RecordDeviceAssemblyStepCommand(
            idempotency_key=idem(), batch_id=batch.id, assembly_step="NEEDLE_INSTALL", component_lot_reference={"lot_id": str(uuid.uuid4())},
        ),
        actor_id,
    )  # unit_identifier omitted -> counts as missing
    await ddcp_commands.record_device_assembly_step(
        db,
        ddcp_commands.RecordDeviceAssemblyStepCommand(
            idempotency_key=idem(), batch_id=batch.id, assembly_step="TIP_CAP", component_lot_reference={"lot_id": str(uuid.uuid4())},
            unit_identifier="UDI-0001",
        ),
        actor_id,
    )

    result = await ddcp_commands.verify_pfs_serialization_compliance(db, batch.id, profile_id)
    assert result["serialization_required"] is True
    assert result["total_device_assembly_records"] == 2
    assert result["missing_identifier_count"] == 1

    not_found_profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-SERIAL-NONE")
    # required_controls has no "serialization" key at all -> not required, missing count not surfaced.
    result_not_required = await ddcp_commands.verify_pfs_serialization_compliance(db, batch.id, not_found_profile.id)
    assert result_not_required["serialization_required"] is False
    assert result_not_required["missing_identifier_count"] == 0


async def test_get_ddcp_change_linkage(seeded, db):
    """PFS-FR-029: the write path already exists (qms.change_commands.assess_impact's own generic
    affected_objects list) -- this is the DDCP-side read confirming the linkage round-trips."""

    actor_id = seeded["users"]["ddcp.operator"].id
    profile = await _create_and_release_profile(db, seeded, actor_id, profile_code="PFS-CHANGE")

    change_receipt = await change_commands.create_change(
        db,
        change_commands.CreateChangeCommand(
            idempotency_key=idem(), site_id=seeded["site_id"], change_number="CHG-DDCP-1", change_type="process",
            classification="permanent", current_state={"barrel": "v1"}, proposed_state={"barrel": "v2"},
            reason="Barrel supplier change", owner_subject_id=actor_id,
        ),
        actor_id,
    )
    await change_commands.assess_impact(
        db,
        change_commands.AssessImpactCommand(
            idempotency_key=idem(), change_id=change_receipt.aggregate_id, expected_version=1,
            affected_objects=[
                {"object_type": "ddcp_profile_version", "object_id": str(profile.id), "impact_category": "risk", "action_required": "Re-validate barrel/stopper compatibility"},
            ],
        ),
        actor_id,
    )

    linkage = await ddcp_commands.get_ddcp_change_linkage(db, "ddcp_profile_version", profile.id)
    assert len(linkage["changes"]) == 1
    assert linkage["changes"][0]["change_number"] == "CHG-DDCP-1"
    assert linkage["changes"][0]["impact_category"] == "risk"

    no_linkage = await ddcp_commands.get_ddcp_change_linkage(db, "ddcp_profile_version", uuid.uuid4())
    assert no_linkage["changes"] == []
