"""Document 17 (SPEC-EBMR-008): yield/potency calculation (delegated to Document 08's released-rule
engine, never a hardcoded formula) and material/packaging/label/component reconciliation, plus the one
genuinely signed action in this document -- independent `verify` (Document 106 row 40).
"""

import uuid

from sqlalchemy import func
from sqlalchemy import select as sa_select

from decimal import Decimal

from app.core.security import hash_password
from app.modules.erp.models import IntegrationReconciliationDifference
from app.modules.iam.models import User, UserSiteRole
from app.modules.qms import service as qms_service
from app.modules.rules.models import UnitOfMeasure
from app.modules.signature.models import SignaturePolicy
from app.modules.yield_reconciliation.models import ManufacturingCalculation, ReconciliationRecord
from app.modules.yield_reconciliation.uom_backfill import backfill_manufacturing_calculations
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username):
    user = User(
        username=username, email=f"{username}@example.com", full_name="Test Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


async def _released_product_and_recipe(client, admin_token, site_id, tag):
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": f"YLDPRD-{tag}", "product_code": f"YLDPRD-{tag}",
            "name": "Yield Test Product", "version_no": 1, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    product_version_id = resp.json()["aggregate_id"]
    await client.post(
        f"/products/v1/drafts/{product_version_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/recipes/v2/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": f"YLDPRD-{tag}", "recipe_code": f"YLDRCP-{tag}", "version_no": 1,
            "product_version_id": product_version_id, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
            "sections": [{"stable_section_code": "SEC-1", "name": "Fill", "sequence": 1}],
            "steps": [{"stable_step_code": "STEP-A", "section_code": "SEC-1", "step_type": "weigh", "sequence_hint": 1}],
            "dependencies": [],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    recipe_version_id = resp.json()["aggregate_id"]
    await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/release",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return product_version_id, recipe_version_id


async def _setup_batch(db, client, seeded, tag):
    admin_token, batch_id, _product_version_id, _recipe_version_id = await _setup_batch_with_product(db, client, seeded, tag)
    return admin_token, batch_id


async def _setup_batch_with_product(db, client, seeded, tag):
    async with db.begin():
        await _make_admin(db, seeded, f"admin.yld{tag}")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, f"admin.yld{tag}")
    product_version_id, recipe_version_id = await _released_product_and_recipe(client, admin_token, seeded["site_id"], tag)

    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": f"BAT-YLD-{tag}",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return admin_token, resp.json()["aggregate_id"], product_version_id, recipe_version_id


async def test_evaluate_yield_normal_calculation(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "1")
    resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95",
            "uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    calc = await db.get(ManufacturingCalculation, uuid.UUID(resp.json()["aggregate_id"]))
    assert calc.state == "CALCULATED"
    assert calc.result["yield_percent"] == "95.00"
    assert calc.rule_object_id is not None
    assert calc.rule_evaluation_id is not None
    # SG-146 (remainder): "kg" has no released rules.gxp_uom row in this environment (no production UOM
    # master data is seeded anywhere in this baseline) -- the free-text uom column stays authoritative
    # and the dual-write is a no-op, exactly the expand-phase contract (nothing breaks).
    assert calc.uom == "kg"
    assert calc.uom_id is None


async def test_evaluate_yield_dual_writes_uom_id_when_a_released_uom_resolves(client, seeded, db):
    """SG-146 (remainder): once a deployment releases a UOM row at the code a caller supplies,
    evaluate_yield's dual-write populates uom_id on the new row without any caller-visible change."""
    async with db.begin():
        db.add(UnitOfMeasure(code="kg-dual", dimension="MASS", base_unit="kg-dual", factor=Decimal("1"), precision_dp=4, status="released"))
    admin_token, batch_id = await _setup_batch(db, client, seeded, "1b")
    resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95",
            "uom": "kg-dual",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    calc = await db.get(ManufacturingCalculation, uuid.UUID(resp.json()["aggregate_id"]))
    assert calc.uom == "kg-dual"
    assert calc.uom_id is not None


async def test_backfill_populates_uom_id_on_existing_rows_idempotently(client, db, seeded):
    """MIG-FR-008/012: the backfill is idempotent (a second run over already-matched rows changes
    nothing) and leaves an unresolvable uom untouched rather than guessing (AG-15)."""
    _admin_token, batch_id = await _setup_batch(db, client, seeded, "1c")
    async with db.begin():
        site_id = seeded["site_id"]
        org_batch = ManufacturingCalculation(
            site_id=site_id, batch_id=uuid.UUID(batch_id), calculation_type="YIELD", input_refs={}, input_hash="x",
            uom="g-backfill", version=1,
        )
        unresolvable = ManufacturingCalculation(
            site_id=site_id, batch_id=uuid.UUID(batch_id), calculation_type="YIELD", input_refs={}, input_hash="y",
            uom="not-a-real-unit", version=1,
        )
        db.add_all([org_batch, unresolvable])
        db.add(UnitOfMeasure(code="g-backfill", dimension="MASS", base_unit="g-backfill", factor=Decimal("1"), precision_dp=4, status="released"))
        await db.flush()
        org_id, unresolvable_id = org_batch.id, unresolvable.id

    async with db.begin():
        result = await backfill_manufacturing_calculations(db, batch_size=500)
    assert result.matched >= 1
    assert result.unmatched >= 1

    matched_row = await db.get(ManufacturingCalculation, org_id)
    unmatched_row = await db.get(ManufacturingCalculation, unresolvable_id)
    assert matched_row.uom_id is not None
    assert unmatched_row.uom_id is None

    # Idempotent: a second pass finds nothing left to do for the row it already matched.
    async with db.begin():
        second = await backfill_manufacturing_calculations(db, batch_size=500)
    assert second.processed == second.unmatched  # only the still-unresolved row is ever revisited


async def test_evaluate_yield_zero_theoretical_quantity_fails_not_crashes(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "2")
    resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "0", "actual_quantity": "95", "uom": "kg"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    calc = await db.get(ManufacturingCalculation, uuid.UUID(resp.json()["aggregate_id"]))
    assert calc.state == "FAILED"
    assert "error" in calc.result


async def test_evaluate_yield_below_min_boundary_out_of_limit(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "3")
    resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "90",
            "uom": "kg", "min_percent": "95",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    calc = await db.get(ManufacturingCalculation, uuid.UUID(resp.json()["aggregate_id"]))
    assert calc.state == "OUT_OF_LIMIT"


async def test_evaluate_yield_manual_source_requires_reason(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "4")
    resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95",
            "uom": "kg", "manual_source": "external LIMS",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text


async def test_evaluate_potency_requires_a_released_rule(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "5")
    resp = await client.post(
        "/manufacturing-calculations/v1/potency/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id, "rule_id": "no_such_potency_rule", "inputs": {}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404, resp.text


async def test_evaluate_material_reconciliation_acceptable(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "6")
    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
            "item_ref": {"material_id": str(uuid.uuid4())}, "uom": "kg",
            "quantities": {"issued": "100.000000", "consumed": "98.000000", "returned": "2.000000"},
            "tolerance_rule": {"type": "absolute", "value": "0.5", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert rec.state == "ACCEPTABLE"
    assert str(rec.variance) == "0.000000"


async def test_evaluate_reconciliation_out_of_tolerance(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "7")
    resp = await client.post(
        "/reconciliation/v1/packaging/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "PACKAGING",
            "item_ref": {"component_id": str(uuid.uuid4())}, "uom": "each",
            "quantities": {"issued": "1000.000000", "consumed": "950.000000", "rejected": "10.000000"},
            "tolerance_rule": {"type": "percentage", "value": "1.0", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert rec.state == "OUT_OF_TOLERANCE"


async def test_reconciliation_type_mismatch_rejected(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "8")
    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "PACKAGING",
            "item_ref": {}, "uom": "kg", "quantities": {"issued": "10"}, "tolerance_rule": {"value": "1"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text


async def test_verify_requires_independent_verifier(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "9")
    evaluate_resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"},
        headers=auth_headers(admin_token),
    )
    calc_id = evaluate_resp.json()["aggregate_id"]

    resp = await client.post(
        f"/reconciliation/v1/{calc_id}/verify",
        json={"idempotency_key": idem(), "record_kind": "CALCULATION", "record_id": calc_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 428, resp.text


async def test_verify_full_flow_with_independent_signer(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "10")
    evaluate_resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"},
        headers=auth_headers(admin_token),
    )
    calc_id = evaluate_resp.json()["aggregate_id"]

    qa_token = await login(client, "qa.reviewer")
    challenge = (
        await client.post(
            f"/reconciliation/v1/{calc_id}/signature-challenges", json={"record_kind": "CALCULATION"}, headers=auth_headers(qa_token)
        )
    ).json()
    resp = await client.post(
        f"/reconciliation/v1/{calc_id}/verify",
        json={
            "idempotency_key": idem(), "record_kind": "CALCULATION", "record_id": calc_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 200, resp.text
    calc = await db.get(ManufacturingCalculation, uuid.UUID(calc_id))
    assert calc.state == "VERIFIED"
    assert calc.verified_signature_id is not None


async def test_batch_summary_release_blocked_until_verified(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "11")
    evaluate_resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "80",
            "uom": "kg", "min_percent": "95",
        },
        headers=auth_headers(admin_token),
    )
    calc_id = evaluate_resp.json()["aggregate_id"]

    summary = (await client.get(f"/reconciliation/v1/batches/{batch_id}/summary", headers=auth_headers(admin_token))).json()
    assert summary["release_blocked"] is True

    qa_token = await login(client, "qa.reviewer")
    challenge = (
        await client.post(f"/reconciliation/v1/{calc_id}/signature-challenges", json={"record_kind": "CALCULATION"}, headers=auth_headers(qa_token))
    ).json()
    resp = await client.post(
        f"/reconciliation/v1/{calc_id}/verify",
        json={
            "idempotency_key": idem(), "record_kind": "CALCULATION", "record_id": calc_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 200, resp.text

    summary = (await client.get(f"/reconciliation/v1/batches/{batch_id}/summary", headers=auth_headers(admin_token))).json()
    assert summary["release_blocked"] is False


async def test_verify_stale_version_rejected(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "12")
    evaluate_resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"},
        headers=auth_headers(admin_token),
    )
    calc_id = evaluate_resp.json()["aggregate_id"]
    qa_token = await login(client, "qa.reviewer")
    challenge = (
        await client.post(f"/reconciliation/v1/{calc_id}/signature-challenges", json={"record_kind": "CALCULATION"}, headers=auth_headers(qa_token))
    ).json()
    resp = await client.post(
        f"/reconciliation/v1/{calc_id}/verify",
        json={
            "idempotency_key": idem(), "record_kind": "CALCULATION", "record_id": calc_id, "expected_version": 99,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


# ---------------------------------------------------------------------------------------------------
# YLD-FR-012 -- LABEL reconciliation consumes Document 16 packaging's own label counts (SG-132 partial).
# ---------------------------------------------------------------------------------------------------


async def _packaging_run_with_labels(client, admin_token, batch_id, *, issued, applied, returned, destroyed, rejected, samples):
    """Drives Document 16's real endpoints, so the counts Document 17 reads back are genuinely
    packaging's own rows -- not fixtures written straight into label_reconciliation."""
    run_id = (
        await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    ).json()["aggregate_id"]
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/line-clearance",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1, "reason": "line cleared for yield test"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/labels/issue",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 2, "quantity_issued": issued},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/reconcile-labels",
        json={
            "idempotency_key": idem(), "run_id": run_id, "expected_version": 3,
            "applied": applied, "returned": returned, "destroyed": destroyed, "rejected": rejected, "samples": samples,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return run_id


async def test_label_reconciliation_consumes_packaging_counts(client, seeded, db):
    """TC-017-012-01. The command takes no quantities at all -- issued/consumed come from Document 16."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "14")
    run_id = await _packaging_run_with_labels(
        client, admin_token, batch_id, issued=100, applied=95, returned=3, destroyed=1, rejected=1, samples=0
    )

    resp = await client.post(
        "/reconciliation/v1/labels/evaluate",
        json={
            "idempotency_key": idem(), "packaging_run_id": run_id,
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert rec.reconciliation_type == "LABEL"
    assert str(rec.batch_id) == batch_id  # derived from the packaging run, not supplied by the caller
    assert rec.quantities["issued"] == "100"
    assert rec.quantities["consumed"] == "95"  # Document 16's `applied`
    assert rec.item_ref["packaging_run_id"] == run_id
    assert rec.item_ref["label_reconciliation_id"] is not None
    assert rec.item_ref["packaging_module_result"] == "balanced"
    assert rec.state == "ACCEPTABLE"
    assert str(rec.variance) == "0.000000"


async def test_label_discrepancy_from_packaging_counts_blocks_release(client, seeded, db):
    """TC-017-S013 (specification scenario: label discrepancy). 100 issued, 95 accounted -> the missing 5
    surface as this module's own OUT_OF_TOLERANCE and the batch's unified release blocker (YLD-FR-012's
    stated intent)."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "15")
    run_id = await _packaging_run_with_labels(
        client, admin_token, batch_id, issued=100, applied=90, returned=3, destroyed=1, rejected=1, samples=0
    )

    resp = await client.post(
        "/reconciliation/v1/labels/evaluate",
        json={
            "idempotency_key": idem(), "packaging_run_id": run_id,
            "tolerance_rule": {"type": "absolute", "value": "1", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert rec.state == "OUT_OF_TOLERANCE"
    assert str(rec.variance) == "5.000000"

    summary = (await client.get(f"/reconciliation/v1/batches/{batch_id}/summary", headers=auth_headers(admin_token))).json()
    assert summary["release_blocked"] is True


async def test_label_reconciliation_without_packaging_counts_fails_closed(client, seeded, db):
    """A run whose labels Document 16 has not reconciled yet has no counts to consume -- the command
    fails closed rather than defaulting to zero."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "16")
    run_id = (
        await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    ).json()["aggregate_id"]

    resp = await client.post(
        "/reconciliation/v1/labels/evaluate",
        json={"idempotency_key": idem(), "packaging_run_id": run_id, "tolerance_rule": {"type": "absolute", "value": "0"}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------------------------------
# YLD-FR-013 / YLD-FR-026 -- COMPONENT reconciliation scoped to Document 12's DeviceUnit (SG-132 partial).
# ---------------------------------------------------------------------------------------------------


async def _device_units(client, admin_token, site_id, batch_id, product_version_id, serials):
    lot_id = (
        await client.post(
            "/devices/v1/lots",
            json={
                "idempotency_key": idem(), "site_id": str(site_id), "product_version_id": product_version_id,
                "batch_id": batch_id, "udi_di": "00012345678905",
            },
            headers=auth_headers(admin_token),
        )
    ).json()["aggregate_id"]
    resp = await client.post(
        "/devices/v1/units/bulk-create",
        json={"idempotency_key": idem(), "device_lot_id": lot_id, "units": [{"serial_number": s} for s in serials]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return [r["aggregate_id"] for r in resp.json()]


async def test_component_reconciliation_scoped_to_device_unit(client, seeded, db):
    """TC-017-013-01 / TC-017-S014 (component scrap). YLD-FR-013's own category vocabulary --
    issued/assembled/rejected/scrapped/returned -- against a real DeviceUnit serial identity."""
    admin_token, batch_id, product_version_id, _ = await _setup_batch_with_product(db, client, seeded, "17")
    unit_id = (await _device_units(client, admin_token, seeded["site_id"], batch_id, product_version_id, ["SN-YLD-1"]))[0]

    resp = await client.post(
        "/reconciliation/v1/components/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "device_unit_id": unit_id,
            "item_ref": {"component_code": "CMP-A"}, "uom": "each",
            "quantities": {"issued": "10", "assembled": "7", "rejected": "1", "scrapped": "1", "returned": "1"},
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert str(rec.device_unit_id) == unit_id
    assert rec.item_ref["serial_number"] == "SN-YLD-1"
    assert rec.state == "ACCEPTABLE"
    assert str(rec.variance) == "0.000000"  # scrapped/assembled genuinely count toward the mass balance


async def test_component_reconciliation_rejects_device_unit_from_another_batch(client, seeded, db):
    """TC-017-013-02. A unit belonging to a different batch is a mis-scoped accountability record and is
    rejected before anything is written."""
    admin_token, batch_a, product_version_id, recipe_version_id = await _setup_batch_with_product(db, client, seeded, "18")
    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": "BAT-YLD-18B",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    batch_b = resp.json()["aggregate_id"]
    unit_id = (await _device_units(client, admin_token, seeded["site_id"], batch_a, product_version_id, ["SN-YLD-18"]))[0]

    resp = await client.post(
        "/reconciliation/v1/components/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_b, "device_unit_id": unit_id,
            "item_ref": {}, "uom": "each", "quantities": {"issued": "1"},
            "tolerance_rule": {"type": "absolute", "value": "0"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"

    # nothing was written for the rejected command
    from sqlalchemy import func, select as sa_select

    from app.modules.yield_reconciliation.models import ReconciliationRecord as RR

    count = (await db.execute(sa_select(func.count()).select_from(RR).where(RR.batch_id == uuid.UUID(batch_b)))).scalar_one()
    assert count == 0


async def test_batch_summary_aggregates_by_device_unit_keeping_exceptions_visible(client, seeded, db):
    """TC-017-026-01. Two serial-scoped rows on one unit aggregate into a single per-unit total, and the
    out-of-tolerance row stays individually identifiable (YLD-FR-026's "without losing exception
    visibility")."""
    admin_token, batch_id, product_version_id, _ = await _setup_batch_with_product(db, client, seeded, "19")
    unit_id = (await _device_units(client, admin_token, seeded["site_id"], batch_id, product_version_id, ["SN-YLD-19"]))[0]

    ok = await client.post(
        "/reconciliation/v1/components/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "device_unit_id": unit_id,
            "item_ref": {"component_code": "CMP-A"}, "uom": "each",
            "quantities": {"issued": "10", "assembled": "10"},
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert ok.status_code == 200, ok.text
    bad = await client.post(
        "/reconciliation/v1/components/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "device_unit_id": unit_id,
            "item_ref": {"component_code": "CMP-B"}, "uom": "each",
            "quantities": {"issued": "5", "assembled": "3"},
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert bad.status_code == 200, bad.text

    summary = (await client.get(f"/reconciliation/v1/batches/{batch_id}/summary", headers=auth_headers(admin_token))).json()
    units = summary["by_device_unit"]
    assert len(units) == 1
    entry = units[0]
    assert entry["device_unit_id"] == unit_id
    assert entry["serial_number"] == "SN-YLD-19"
    assert entry["record_count"] == 2
    assert entry["totals"]["issued"] == "15"
    assert entry["totals"]["assembled"] == "13"
    assert entry["unresolved_record_ids"] == [bad.json()["aggregate_id"]]
    assert summary["release_blocked"] is True


async def test_batch_summary_omits_units_for_unscoped_reconciliation(client, seeded, db):
    """A MATERIAL reconciliation has no per-unit identity and must not invent one."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "20")
    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
            "item_ref": {"material_id": str(uuid.uuid4())}, "uom": "kg",
            "quantities": {"issued": "100.000000", "consumed": "100.000000"},
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    summary = (await client.get(f"/reconciliation/v1/batches/{batch_id}/summary", headers=auth_headers(admin_token))).json()
    assert summary["by_device_unit"] == []


# ---------------------------------------------------------------------------------------------------
# YLD-FR-021 -- approved loss is documented, and its approval links to QMS's deviation (SG-132 partial).
# ---------------------------------------------------------------------------------------------------


def _loss_body(batch_id, **overrides):
    body = {
        "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
        "item_ref": {"material_id": str(uuid.uuid4())}, "uom": "kg",
        "quantities": {"issued": "100.000000", "consumed": "95.000000", "approved_loss": "5.000000"},
        "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
    }
    body.update(overrides)
    return body


async def test_approved_loss_without_documented_reason_is_rejected(client, seeded, db):
    """TC-017-021-01 (negative half). An approved loss with no documented reason is an unexplained
    variance wearing an approved label — it must not persist."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "21")
    resp = await client.post(
        "/reconciliation/v1/material/evaluate", json=_loss_body(batch_id), headers=auth_headers(admin_token)
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"

    summary = (await client.get(f"/reconciliation/v1/batches/{batch_id}/summary", headers=auth_headers(admin_token))).json()
    assert summary["reconciliations"] == []


async def test_approved_loss_with_documented_reasons_is_accepted(client, seeded, db):
    """TC-017-021-01. YLD-FR-021's own named categories are used as data, not as a closed enum."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "22")
    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json=_loss_body(batch_id, loss_reasons=[
            {"category": "process_loss", "description": "line hold-up in transfer piping", "quantity": "3.000000"},
            {"category": "spill", "description": "spill during charge, cleaned and documented", "quantity": "2.000000"},
        ]),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert rec.state == "ACCEPTABLE"
    assert str(rec.variance) == "0.000000"
    assert [r["category"] for r in rec.loss_reasons] == ["process_loss", "spill"]


async def test_partial_loss_reason_quantities_are_rejected(client, seeded, db):
    """A reason set that accounts for only part of the approved loss must not pass as a complete
    explanation."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "23")
    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json=_loss_body(batch_id, loss_reasons=[
            {"category": "process_loss", "description": "hold-up", "quantity": "3.000000"},
        ]),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text


async def test_approved_loss_links_to_qms_deviation(client, seeded, db):
    """TC-017-021-01 (approval half). QMS owns the deviation; Document 17 links to one that already
    exists and copies its quality_event_id — it never creates a deviation itself (AG-05)."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "24")

    dev = await client.post(
        "/qms/v1/deviations",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "deviation_number": "DEV-YLD-24",
            "deviation_type": "process", "source_type": "batch", "source_id": batch_id,
            "severity": "minor", "owner_subject_id": str(seeded["users"]["qa.reviewer"].id),
        },
        headers=auth_headers(admin_token),
    )
    assert dev.status_code == 200, dev.text
    deviation_id = dev.json()["aggregate_id"]

    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json=_loss_body(batch_id, linked_deviation_id=deviation_id, loss_reasons=[
            {"category": "process_loss", "description": "approved under DEV-YLD-24"},
        ]),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    deviation = await qms_service.get_deviation(db, uuid.UUID(deviation_id))
    assert rec.linked_quality_event_id == deviation.quality_event_id


# ---------------------------------------------------------------------------------------------------
# YLD-FR-027 -- ERP/WMS comparison flags a difference but never overwrites GxP evidence (SG-132 partial).
# ---------------------------------------------------------------------------------------------------


async def _erp_reconciliation_run(client, admin_token, seeded):
    resp = await client.post(
        "/integration/v1/reconciliation-runs",
        json={
            "idempotency_key": idem(), "erp_instance_id": str(seeded["erp_instance"].id),
            "scope": "batch-material", "reconciliation_type": "INVENTORY", "cutoff_at": "2026-08-27T00:00:00Z",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_matching_external_quantity_records_comparison_without_a_difference(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "25")
    run_id = await _erp_reconciliation_run(client, admin_token, seeded)

    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
            "item_ref": {}, "uom": "kg",
            "quantities": {"issued": "100.000000", "consumed": "100.000000"},
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
            "external_reference": {"system": "ERP", "quantity": "100.000000", "erp_run_id": run_id},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert rec.external_comparison["matched"] is True
    assert rec.external_comparison["erp_difference_id"] is None


async def test_external_discrepancy_flags_erp_difference_but_never_overwrites_variance(client, seeded, db):
    """TC-017-027-01 / TC-017-S015. ERP says 92, GxP computed 100 — the GxP variance and state are
    untouched and the mismatch is raised in Document 53's difference ledger instead."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "26")
    run_id = await _erp_reconciliation_run(client, admin_token, seeded)

    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
            "item_ref": {}, "uom": "kg",
            "quantities": {"issued": "100.000000", "consumed": "100.000000"},
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
            "external_reference": {"system": "ERP", "quantity": "92.000000", "erp_run_id": run_id},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))

    # GxP evidence is exactly what the GxP calculation produced — ERP did not touch it.
    assert str(rec.variance) == "0.000000"
    assert rec.state == "ACCEPTABLE"
    assert rec.quantities["accounted"] == "100.000000"

    # ...and the discrepancy is flagged in the ERP ledger, OPEN for a human.
    assert rec.external_comparison["matched"] is False
    assert rec.external_comparison["difference"] == "-8.000000"
    difference = await db.get(IntegrationReconciliationDifference, uuid.UUID(rec.external_comparison["erp_difference_id"]))
    assert difference.difference_type == "VALUE_MISMATCH"
    assert difference.resolution_status == "OPEN"
    assert difference.internal_value == {"quantity": "100.000000", "uom": "kg"}
    assert difference.external_value == {"quantity": "92.000000", "uom": "kg"}


async def test_external_comparison_boundary_smallest_representable_difference(client, seeded, db):
    """TC-017-027-03. One unit in the last decimal place is still a discrepancy — the comparison is an
    exact Decimal equality, not a tolerance (the tolerance belongs to the GxP mass balance, not to the
    ERP cross-check)."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "28")
    run_id = await _erp_reconciliation_run(client, admin_token, seeded)
    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
            "item_ref": {}, "uom": "kg",
            "quantities": {"issued": "100.000000", "consumed": "100.000000"},
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
            "external_reference": {"system": "ERP", "quantity": "100.000001", "erp_run_id": run_id},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert rec.external_comparison["matched"] is False
    assert rec.external_comparison["difference"] == "0.000001"
    assert rec.external_comparison["erp_difference_id"] is not None


async def test_replayed_evaluate_does_not_raise_a_second_erp_difference(client, seeded, db):
    """TC-017-027-04. The ERP difference is written under an idempotency key derived from the evaluate
    command's own key, so replaying the command cannot inflate the difference ledger."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "29")
    run_id = await _erp_reconciliation_run(client, admin_token, seeded)
    body = {
        "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
        "item_ref": {}, "uom": "kg",
        "quantities": {"issued": "10.000000", "consumed": "10.000000"},
        "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
        "external_reference": {"system": "ERP", "quantity": "9.000000", "erp_run_id": run_id},
    }
    first = await client.post("/reconciliation/v1/material/evaluate", json=body, headers=auth_headers(admin_token))
    second = await client.post("/reconciliation/v1/material/evaluate", json=body, headers=auth_headers(admin_token))
    assert first.status_code == 200 and second.status_code == 200, (first.text, second.text)
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]

    count = (
        await db.execute(
            sa_select(func.count()).select_from(IntegrationReconciliationDifference)
            .where(IntegrationReconciliationDifference.run_id == uuid.UUID(run_id))
        )
    ).scalar_one()
    assert count == 1


async def test_external_discrepancy_without_erp_run_is_recorded_but_not_flagged(client, seeded, db):
    """No ERP run to attach to: the comparison still happens and is recorded, it just has nowhere to
    raise a difference — it must not silently claim it flagged one."""
    admin_token, batch_id = await _setup_batch(db, client, seeded, "27")
    resp = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
            "item_ref": {}, "uom": "kg",
            "quantities": {"issued": "50.000000", "consumed": "50.000000"},
            "tolerance_rule": {"type": "absolute", "value": "0", "inclusive": True},
            "external_reference": {"system": "WMS", "quantity": "48.000000"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rec = await db.get(ReconciliationRecord, uuid.UUID(resp.json()["aggregate_id"]))
    assert rec.external_comparison["matched"] is False
    assert rec.external_comparison["erp_difference_id"] is None
    assert "no erp_run_id" in rec.external_comparison["flagged"]
    assert str(rec.variance) == "0.000000"


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": str(uuid.uuid4()), "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"},
        headers={},
    )
    assert resp.status_code == 401


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "13")
    key = idem()
    body = {"idempotency_key": key, "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"}
    first = await client.post("/manufacturing-calculations/v1/yield/evaluate", json=body, headers=auth_headers(admin_token))
    second = await client.post("/manufacturing-calculations/v1/yield/evaluate", json=body, headers=auth_headers(admin_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


# =================================================================================================
# YLD-FR-022 "correction preserves original" -- supersede (WP-03 gap resolution)
# =================================================================================================


async def test_evaluate_yield_supersede_flags_original_and_links_correction(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "14")
    original = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"},
        headers=auth_headers(admin_token),
    )
    assert original.status_code == 200, original.text
    original_id = original.json()["aggregate_id"]

    correction = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "97",
            "uom": "kg", "supersedes_id": original_id, "reason": "actual_quantity was transcribed wrong",
        },
        headers=auth_headers(admin_token),
    )
    assert correction.status_code == 200, correction.text
    correction_id = correction.json()["aggregate_id"]

    original_row = await db.get(ManufacturingCalculation, uuid.UUID(original_id))
    correction_row = await db.get(ManufacturingCalculation, uuid.UUID(correction_id))
    assert original_row.state == "SUPERSEDED"
    assert correction_row.supersedes_id == original_row.id
    assert correction_row.result["yield_percent"] == "97.00"

    from app.modules.audit.models import AuditEvent
    from app.modules.mutation.models import OutboxEvent
    corrected_audit = await db.scalar(
        sa_select(AuditEvent).where(AuditEvent.aggregate_id == original_row.id, AuditEvent.action == "Corrected")
    )
    assert corrected_audit is not None and corrected_audit.reason == "actual_quantity was transcribed wrong"
    superseded_event = await db.scalar(
        sa_select(OutboxEvent).where(
            OutboxEvent.aggregate_id == original_row.id, OutboxEvent.event_type == "ReconciliationSuperseded",
        )
    )
    assert superseded_event is not None
    assert superseded_event.payload["corrected_by_id"] == correction_id


async def test_evaluate_yield_supersede_requires_reason(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "15")
    original = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"},
        headers=auth_headers(admin_token),
    )
    original_id = original.json()["aggregate_id"]

    resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "97",
            "uom": "kg", "supersedes_id": original_id,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_evaluate_yield_supersede_rejects_already_superseded_original(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "16")
    original = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"},
        headers=auth_headers(admin_token),
    )
    original_id = original.json()["aggregate_id"]
    first_correction = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "97",
            "uom": "kg", "supersedes_id": original_id, "reason": "first correction",
        },
        headers=auth_headers(admin_token),
    )
    assert first_correction.status_code == 200, first_correction.text

    second_correction = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "theoretical_quantity": "100", "actual_quantity": "98",
            "uom": "kg", "supersedes_id": original_id, "reason": "trying to correct the same original twice",
        },
        headers=auth_headers(admin_token),
    )
    assert second_correction.status_code == 422, second_correction.text
    assert second_correction.json()["code"] == "VALIDATION_FAILED"


async def test_evaluate_material_reconciliation_supersede_flags_original(client, seeded, db):
    admin_token, batch_id = await _setup_batch(db, client, seeded, "17")
    original = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
            "item_ref": {"material_id": str(uuid.uuid4())}, "uom": "kg",
            "quantities": {"issued": "100.000000", "consumed": "98.000000", "returned": "2.000000"},
            "tolerance_rule": {"type": "absolute", "value": "0.5", "inclusive": True},
        },
        headers=auth_headers(admin_token),
    )
    assert original.status_code == 200, original.text
    original_id = original.json()["aggregate_id"]

    correction = await client.post(
        "/reconciliation/v1/material/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "reconciliation_type": "MATERIAL",
            "item_ref": {"material_id": str(uuid.uuid4())}, "uom": "kg",
            "quantities": {"issued": "100.000000", "consumed": "97.000000", "returned": "3.000000"},
            "tolerance_rule": {"type": "absolute", "value": "0.5", "inclusive": True},
            "supersedes_id": original_id, "reason": "returned quantity was miscounted",
        },
        headers=auth_headers(admin_token),
    )
    assert correction.status_code == 200, correction.text

    original_row = await db.get(ReconciliationRecord, uuid.UUID(original_id))
    correction_row = await db.get(ReconciliationRecord, uuid.UUID(correction.json()["aggregate_id"]))
    assert original_row.state == "SUPERSEDED"
    assert correction_row.supersedes_id == original_row.id


async def test_supersede_rejects_a_record_from_a_different_batch(client, seeded, db):
    admin_token, batch_id_1, product_version_id, recipe_version_id = await _setup_batch_with_product(db, client, seeded, "18")
    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": "BAT-YLD-18b",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    batch_id_2 = resp.json()["aggregate_id"]

    original = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={"idempotency_key": idem(), "batch_id": batch_id_1, "theoretical_quantity": "100", "actual_quantity": "95", "uom": "kg"},
        headers=auth_headers(admin_token),
    )
    original_id = original.json()["aggregate_id"]

    resp = await client.post(
        "/manufacturing-calculations/v1/yield/evaluate",
        json={
            "idempotency_key": idem(), "batch_id": batch_id_2, "theoretical_quantity": "100", "actual_quantity": "97",
            "uom": "kg", "supersedes_id": original_id, "reason": "wrong batch on purpose",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"
