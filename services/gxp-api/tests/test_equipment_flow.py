"""Document 38 (SPEC-EQP-001) thin slice: create -> qualify -> calibrate -> return-to-service (the one
place QUALIFIED_AVAILABLE is ever written), plus the negative/concurrency/signature cases the test-case
book (test-cases/WP-06/Document_38_SPEC-EQP-001_TEST_CASES.md) exercises. Mirrors the discipline used in
tests/test_material_flow.py.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError

from sqlalchemy import select

from app.modules.batch_execution.models import Batch
from app.modules.equipment.models import EquipmentUseLog
from app.modules.iam.models import Role, UserSiteRole
from app.modules.product_master.models import ProductVersion
from app.modules.recipe_master.models import RecipeFamily, RecipeVersion
from app.modules.supplier_quality.models import Supplier
from tests.conftest import auth_headers, idem, login


async def _create_batch(db, seeded, *, batch_number: str) -> Batch:
    # Same minimal direct-insert pattern test_ddcp_flow.py's own _create_batch() uses -- equipment's
    # reservation feature only needs a real batch_id to satisfy EquipmentUseLog's FK, not a full
    # product/recipe/batch command flow.
    site_id = seeded["site_id"]
    pv = ProductVersion(
        product_business_id=f"PB-{batch_number}", version_no=1, product_code=f"PROD-{batch_number}",
        name="Test Equipment Reservation Product", manufacturing_profile_code="pharma",
        lifecycle_state="released", site_id=site_id,
    )
    db.add(pv)
    await db.flush()
    rf = RecipeFamily(
        product_business_id=pv.product_business_id, recipe_code=f"RCP-{batch_number}", site_id=site_id,
        manufacturing_profile_code="pharma",
    )
    db.add(rf)
    await db.flush()
    rv = RecipeVersion(
        recipe_family_id=rf.id, version_no=1, product_version_id=pv.id, site_id=site_id,
        lifecycle_state="released",
    )
    db.add(rv)
    await db.flush()
    batch = Batch(
        site_id=site_id, batch_number=batch_number, product_version_id=pv.id, recipe_version_id=rv.id,
        target_qty=Decimal("1000"), target_uom="EA", state="in_execution", version=1,
    )
    db.add(batch)
    await db.flush()
    return batch


async def _create_equipment_class(client):
    # Bug fix (equipment_class_id now required/validated at creation, see commands.py) needs a real,
    # existing EquipmentClass row to reference. This table has its own create endpoint under
    # recipe_master (`/recipes/v2/equipment-classes`, `recipe.author` permission, Admin holds it) — a
    # fresh class per call avoids class_code collisions across the many _create_asset() call sites in
    # this file.
    pe_token = await login(client, "process.engineer")
    resp = await client.post(
        "/recipes/v2/equipment-classes",
        json={"idempotency_key": idem(), "class_code": f"CLASS-{uuid.uuid4().hex[:12]}", "name": "Test class"},
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _create_asset(client, token, site_id, equipment_code="EQP-1"):
    equipment_class_id = await _create_equipment_class(client)
    resp = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "equipment_code": equipment_code,
            "equipment_class_id": equipment_class_id, "is_computer_operated": False, "manufacturer": "Acme", "model": "M1", "serial_no": "SN-1",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _qualify(client, token, asset_id, expected_version, qualified=True):
    resp = await client.post(
        f"/equipment/v1/{asset_id}/qualifications",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": expected_version,
            "qualification_status": "PQ_COMPLETE" if qualified else "IQ_COMPLETE", "qualified": qualified,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _calibrate(client, token, asset_id, expected_version, result="pass"):
    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": expected_version,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": result,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _approve_calibration(client, token, asset_id, expected_version, calibration_id, approved=True):
    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": expected_version,
            "calibration_id": calibration_id, "approved": approved,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _latest_calibration_id(client, token, asset_id):
    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(token))).json()
    return history["calibrations"][0]["id"]


async def _return_to_service(client, token, asset_id, expected_version):
    return await client.post(
        f"/equipment/v1/{asset_id}/return-to-service",
        json={"idempotency_key": idem(), "asset_id": asset_id, "expected_version": expected_version},
        headers=auth_headers(token),
    )


async def _hold(client, token, asset_id, expected_version, challenge_id, reauth_password="ChangeMe123!", reason="Investigating"):
    return await client.post(
        f"/equipment/v1/{asset_id}/hold",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": expected_version,
            "reason": reason, "challenge_id": challenge_id, "reauth_password": reauth_password,
        },
        headers=auth_headers(token),
    )


async def test_create_asset_enters_installed(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(admin_token))).json()
    assert detail["state"] == "INSTALLED"
    assert detail["version"] == 1


async def test_create_asset_without_code_auto_generates(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    equipment_class_id = await _create_equipment_class(client)
    resp = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "equipment_class_id": equipment_class_id, "is_computer_operated": False,
            "manufacturer": "Acme", "model": "M1",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    asset_id = resp.json()["aggregate_id"]
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(admin_token))).json()
    assert detail["equipment_code"].startswith("EQP-")

    resp2 = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "equipment_class_id": equipment_class_id, "is_computer_operated": False,
            "manufacturer": "Acme", "model": "M2",
        },
        headers=auth_headers(admin_token),
    )
    assert resp2.status_code == 200, resp2.text
    detail2 = (await client.get(f"/equipment/v1/assets/{resp2.json()['aggregate_id']}", headers=auth_headers(admin_token))).json()
    assert detail2["equipment_code"] != detail["equipment_code"]


async def test_create_asset_requires_equipment_administrator_role(client, seeded):
    op_token = await login(client, "operator1")
    # A real equipment_class_id so the request reaches the RBAC check this test is actually about
    # (equipment_class_id is a required field -- an invalid/missing one would 422 before ever reaching
    # evaluate_policy, proving nothing about the role gate).
    equipment_class_id = await _create_equipment_class(client)
    resp = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "equipment_class_id": equipment_class_id, "is_computer_operated": False,
            "equipment_code": "EQP-X",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_full_qualify_calibrate_return_to_service_flow(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    eng_token = await login(client, "engineering.manager")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    receipt = await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    assert receipt["resulting_version"] == 2

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "VERIFICATION"
    assert detail["qualification_status"] == "QUALIFIED"

    receipt = await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    assert receipt["resulting_version"] == 3
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    # Client gap-analysis Phase 4: a passing result alone is not yet "current" -- it needs the separate
    # QA approval step below first (Pass/Fail is objective, Approved/Not-Approved is a distinct gate).
    assert detail["calibration_status"] == "pending_approval"

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(eng_token))).json()
    assert eligibility["eligible"] is False
    assert any(r["code"] == "CALIBRATION_APPROVAL_PENDING" for r in eligibility["reasons"])

    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)
    receipt = await _approve_calibration(client, qa_token, asset_id, expected_version=3, calibration_id=calibration_id)
    assert receipt["resulting_version"] == 4
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["calibration_status"] == "current"

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(eng_token))).json()
    assert eligibility["eligible"] is True
    assert eligibility["reasons"] == []

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=4)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "QUALIFIED_AVAILABLE"


async def test_return_to_service_rejected_without_qualification(client, seeded):
    admin_token = await login(client, "equipment.admin")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    resp = await _return_to_service(client, eng_token, asset_id, expected_version=1)
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"  # INSTALLED is not a returnable state yet


async def test_oot_calibration_holds_equipment_and_blocks_return(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    receipt = await _calibrate(client, cal_token, asset_id, expected_version=2, result="oot")
    assert receipt["resulting_version"] == 3
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "OUT_OF_SERVICE"
    assert detail["hold_flag"] is True
    assert detail["calibration_status"] == "oot"

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    assert history["calibrations"][0]["impact_assessment_required"] is True

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(eng_token))).json()
    assert eligibility["eligible"] is False
    assert any(r["code"] == "CALIBRATION_OOT_IMPACT_REQUIRED" for r in eligibility["reasons"])

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=3)
    assert resp.status_code == 409
    assert resp.json()["code"] == "CALIBRATION_OOT_IMPACT_REQUIRED"

    # A subsequent passing calibration clears the hold, but still needs QA approval (Phase 4) before
    # return to service succeeds.
    qa_token = await login(client, "qa.releaser")
    receipt = await _calibrate(client, cal_token, asset_id, expected_version=3, result="pass")
    assert receipt["resulting_version"] == 4
    resp = await _return_to_service(client, eng_token, asset_id, expected_version=4)
    assert resp.status_code == 409
    assert resp.json()["code"] == "CALIBRATION_APPROVAL_PENDING"

    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)
    receipt = await _approve_calibration(client, qa_token, asset_id, expected_version=4, calibration_id=calibration_id)
    assert receipt["resulting_version"] == 5
    resp = await _return_to_service(client, eng_token, asset_id, expected_version=5)
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Calibration approval -- Client gap-analysis Phase 4 (2026-10-05): "Pass/Fail" (objective result) is
# distinct from "Approved/Not-Approved" (a separate QA disposition), SoD-enforced.
# ---------------------------------------------------------------------------


async def test_calibrate_requires_result_fields_when_not_approving(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={"idempotency_key": idem(), "asset_id": asset_id, "expected_version": 2},
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_approve_calibration_requires_distinct_role_from_calibrate(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, cal_token, asset_id)

    # Calibration Technician holds equipment_asset.calibrate but not equipment_asset.approve_calibration.
    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 3,
            "calibration_id": calibration_id, "approved": True,
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_approve_calibration_rejects_same_performer_sod(client, seeded, db):
    # No seeded test user holds the "Admin" role by default (unlike the live demo's scripts/seed.py --
    # tests/conftest.py's fixture deliberately keeps Calibration Technician / QA Releaser disjoint).
    # Promote operator1 to also hold Admin -- same `_promote_to_admin` technique test_iam_admin.py uses --
    # so a single actor holds both equipment_asset.calibrate and equipment_asset.approve_calibration and
    # this test exercises the SoD check itself, not merely a missing-permission rejection.
    site_id = seeded["site_id"]
    async with db.begin():
        admin_role = (await db.execute(select(Role).where(Role.name == "Admin"))).scalar_one()
        db.add(UserSiteRole(user_id=seeded["users"]["operator1"].id, site_id=site_id, role_id=admin_role.id))

    equip_admin_token = await login(client, "equipment.admin")
    actor_token = await login(client, "operator1")
    asset_id = await _create_asset(client, equip_admin_token, site_id)
    await _qualify(client, equip_admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, actor_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, actor_token, asset_id)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 3,
            "calibration_id": calibration_id, "approved": True,
        },
        headers=auth_headers(actor_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"
    assert "sod" in resp.json()["message"].lower() or "independent" in resp.json()["message"].lower()


async def test_approve_calibration_rejected_is_not_eligible(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.releaser")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)

    receipt = await _approve_calibration(
        client, qa_token, asset_id, expected_version=3, calibration_id=calibration_id, approved=False
    )
    assert receipt["resulting_version"] == 4
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["calibration_status"] == "rejected"

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(eng_token))).json()
    assert eligibility["eligible"] is False
    assert any(r["code"] == "CALIBRATION_APPROVAL_PENDING" for r in eligibility["reasons"])

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    cal = history["calibrations"][0]
    assert cal["approved"] is False
    assert cal["approved_by_user_id"] is not None
    assert cal["approved_at"] is not None


async def test_approve_calibration_twice_rejected(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.releaser")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)

    await _approve_calibration(client, qa_token, asset_id, expected_version=3, calibration_id=calibration_id)
    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 4,
            "calibration_id": calibration_id, "approved": True,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_approve_older_calibration_does_not_resurrect_status_over_newer_one(client, seeded):
    """Two calibrations get recorded before either is reviewed (e.g. a quick retry); approving the
    *older* one must not flip the asset to "current" while the newer one is still unreviewed -- only the
    latest calibration's own approval may change asset.calibration_status (commands.py's own `latest.id
    == calibration.id` guard)."""
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.releaser")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    older_calibration_id = history["calibrations"][0]["id"]

    await _calibrate(client, cal_token, asset_id, expected_version=3, result="pass")
    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    newer_calibration_id = history["calibrations"][0]["id"]
    assert newer_calibration_id != older_calibration_id

    receipt = await _approve_calibration(
        client, qa_token, asset_id, expected_version=4, calibration_id=older_calibration_id
    )
    assert receipt["resulting_version"] == 5
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["calibration_status"] == "pending_approval"  # still gated on the newer, unreviewed one

    receipt = await _approve_calibration(
        client, qa_token, asset_id, expected_version=5, calibration_id=newer_calibration_id
    )
    assert receipt["resulting_version"] == 6
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["calibration_status"] == "current"


async def test_approve_calibration_unknown_calibration_id_not_found(client, seeded):
    admin_token = await login(client, "equipment.admin")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 1,
            "calibration_id": str(uuid.uuid4()), "approved": True,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "NOT_FOUND"


async def test_hold_requires_signature_and_reason(client, seeded):
    admin_token = await login(client, "equipment.admin")
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)

    challenge = (
        await client.post(
            f"/equipment/v1/{asset_id}/signature-challenges", json={"action": "hold"}, headers=auth_headers(op_token),
        )
    ).json()

    # Wrong reauth password -> no valid signature was ever produced.
    resp = await _hold(client, op_token, asset_id, expected_version=1, challenge_id=challenge["challenge_id"], reauth_password="wrong-password")
    assert resp.status_code == 428
    assert resp.json()["code"] == "MISSING_SIGNATURE"

    # Correct password + valid challenge succeeds and holds the asset.
    resp = await _hold(client, op_token, asset_id, expected_version=1, challenge_id=challenge["challenge_id"])
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(op_token))).json()
    assert detail["state"] == "SUSPENDED"
    assert detail["hold_flag"] is True
    assert detail["hold_reason"] == "Investigating"


async def test_hold_requires_role(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    challenge = (
        await client.post(
            f"/equipment/v1/{asset_id}/signature-challenges", json={"action": "hold"}, headers=auth_headers(admin_token),
        )
    ).json()
    resp = await _hold(client, admin_token, asset_id, expected_version=1, challenge_id=challenge["challenge_id"])
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_stale_version_rejected(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=False)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/qualifications",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 1,
            "qualification_status": "IQ_COMPLETE", "qualified": False,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_breakdown_maintenance_holds_then_verification_returns_to_service(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.releaser")
    maint_token = await login(client, "maintenance.tech")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)
    await _approve_calibration(client, qa_token, asset_id, expected_version=3, calibration_id=calibration_id)
    await _return_to_service(client, eng_token, asset_id, expected_version=4)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 5,
            "type": "corrective", "fault_description": "Motor stall",
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "OUT_OF_SERVICE"
    assert detail["hold_flag"] is True

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    wo_id = history["maintenance_work_orders"][0]["id"]

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 6,
            "work_order_id": wo_id, "work_performed": "Replaced motor", "verified": True,
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "VERIFICATION"
    assert detail["maintenance_status"] == "complete"

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=7)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "QUALIFIED_AVAILABLE"


async def test_breakdown_maintenance_type_holds_equipment(client, seeded):
    """Client requirement #9: "breakdown" is a distinct MAINTENANCE_TYPES value (alongside planned/
    corrective) that triggers the same hold/OUT_OF_SERVICE side effect corrective already does."""
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.releaser")
    maint_token = await login(client, "maintenance.tech")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)
    await _approve_calibration(client, qa_token, asset_id, expected_version=3, calibration_id=calibration_id)
    await _return_to_service(client, eng_token, asset_id, expected_version=4)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 5,
            "type": "breakdown", "fault_description": "Sudden pump failure",
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "OUT_OF_SERVICE"
    assert detail["hold_flag"] is True

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    work_order = history["maintenance_work_orders"][0]
    assert work_order["type"] == "breakdown"

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 6,
            "work_order_id": work_order["id"], "work_performed": "Replaced pump seal", "verified": True,
            "actual_downtime_hours": "6.50",
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    assert history["maintenance_work_orders"][0]["actual_downtime_hours"] == "6.50"


async def test_breakdown_requires_new_approved_calibration_before_return_to_service(client, seeded):
    """Client gap-analysis Phase 7 (2026-10-05): a breakdown defaults to requiring recalibration before
    the equipment is eligible again -- verified maintenance alone is not enough, same two-step bar
    CALIBRATION_APPROVAL_PENDING already applies to a plain passing result."""
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.releaser")
    maint_token = await login(client, "maintenance.tech")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)
    await _approve_calibration(client, qa_token, asset_id, expected_version=3, calibration_id=calibration_id)
    await _return_to_service(client, eng_token, asset_id, expected_version=4)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 5,
            "type": "breakdown", "fault_description": "Power supply failure, suspected drift",
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["recalibration_required"] is True

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    work_order_id = history["maintenance_work_orders"][0]["id"]
    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 6,
            "work_order_id": work_order_id, "work_performed": "Replaced power supply", "verified": True,
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text

    # Verified maintenance alone does not clear recalibration_required -- return-to-service still blocks.
    resp = await _return_to_service(client, eng_token, asset_id, expected_version=7)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "RECALIBRATION_REQUIRED"

    await _calibrate(client, cal_token, asset_id, expected_version=7, result="pass")
    calibration_id2 = await _latest_calibration_id(client, eng_token, asset_id)
    assert calibration_id2 != calibration_id

    # A new calibration recorded but not yet approved still blocks on the calibration-approval gate first.
    resp = await _return_to_service(client, eng_token, asset_id, expected_version=8)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "CALIBRATION_APPROVAL_PENDING"

    await _approve_calibration(client, qa_token, asset_id, expected_version=8, calibration_id=calibration_id2)
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["recalibration_required"] is False

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=9)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "QUALIFIED_AVAILABLE"


async def test_breakdown_flagged_non_critical_skips_recalibration_gate(client, seeded):
    """The client's own example: a mere power-supply failure flagged non-critical skips the recalibration
    requirement -- verified maintenance alone is enough to return to service."""
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.releaser")
    maint_token = await login(client, "maintenance.tech")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)
    await _approve_calibration(client, qa_token, asset_id, expected_version=3, calibration_id=calibration_id)
    await _return_to_service(client, eng_token, asset_id, expected_version=4)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 5,
            "type": "breakdown", "fault_description": "Power supply failure", "non_critical": True,
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["recalibration_required"] is False

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    work_order_id = history["maintenance_work_orders"][0]["id"]
    assert history["maintenance_work_orders"][0]["non_critical"] is True
    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 6,
            "work_order_id": work_order_id, "work_performed": "Swapped power supply", "verified": True,
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=7)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(eng_token))).json()
    assert detail["state"] == "QUALIFIED_AVAILABLE"


async def test_create_asset_requires_is_computer_operated(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    equipment_class_id = await _create_equipment_class(client)
    resp = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "equipment_class_id": equipment_class_id,
            "equipment_code": "EQP-NO-CSV-FLAG",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_create_asset_persists_is_computer_operated(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    equipment_class_id = await _create_equipment_class(client)
    resp = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "equipment_class_id": equipment_class_id,
            "equipment_code": "EQP-CSV-FLAG", "is_computer_operated": True,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    asset_id = resp.json()["aggregate_id"]
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(admin_token))).json()
    assert detail["is_computer_operated"] is True


async def test_planned_maintenance_activity_checklist_round_trips(client, seeded):
    """Client gap-analysis Phase 7: the car-service-style Activity/Result checklist, recorded at
    completion time for a "planned" work order."""
    admin_token = await login(client, "equipment.admin")
    maint_token = await login(client, "maintenance.tech")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 1,
            "type": "planned", "work_performed": "Scheduled PM",
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    work_order_id = history["maintenance_work_orders"][0]["id"]

    activities = [
        {"activity": "Check belt tension", "result": "OK"},
        {"activity": "Lubricate bearings", "result": "Done"},
    ]
    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 2,
            "work_order_id": work_order_id, "verified": True, "activities": activities,
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(eng_token))).json()
    assert history["maintenance_work_orders"][0]["activities"] == activities


async def test_bulk_import_equipment_preview_and_commit(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    equipment_class_id = await _create_equipment_class(client)
    class_code_resp = await client.get(f"/equipment/v1/equipment-classes", headers=auth_headers(admin_token))
    class_code = next(c["class_code"] for c in class_code_resp.json() if c["id"] == equipment_class_id)

    rows = [
        {"equipment_class_code": class_code, "manufacturer": "Acme", "is_computer_operated": False},
        {"equipment_class_code": "NOT-A-REAL-CLASS", "manufacturer": "Acme"},
    ]
    preview = await client.post(
        "/equipment/v1/assets/bulk-import/preview", json={"rows": rows}, headers=auth_headers(admin_token)
    )
    assert preview.status_code == 200, preview.text
    outcomes = preview.json()
    assert outcomes[0]["ok"] is True
    assert outcomes[1]["ok"] is False
    assert "NOT-A-REAL-CLASS" in outcomes[1]["error"]

    # All-or-nothing: committing the same batch (one bad row) creates nothing.
    bad_commit = await client.post(
        "/equipment/v1/assets/bulk-import/commit",
        json={"idempotency_key": idem(), "site_id": str(site_id), "rows": rows},
        headers=auth_headers(admin_token),
    )
    assert bad_commit.status_code == 422, bad_commit.text

    good_rows = [{"equipment_class_code": class_code, "manufacturer": "Acme", "is_computer_operated": True}]
    commit = await client.post(
        "/equipment/v1/assets/bulk-import/commit",
        json={"idempotency_key": idem(), "site_id": str(site_id), "rows": good_rows},
        headers=auth_headers(admin_token),
    )
    assert commit.status_code == 200, commit.text
    created = commit.json()["created"]
    assert len(created) == 1
    detail = (await client.get(f"/equipment/v1/assets/{created[0]['asset_id']}", headers=auth_headers(admin_token))).json()
    assert detail["is_computer_operated"] is True
    assert detail["equipment_code"] == created[0]["equipment_code"]


async def test_record_calibration_internal_default(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(cal_token))).json()
    assert history["calibrations"][0]["calibration_type"] == "internal"
    assert history["calibrations"][0]["provider_name"] is None


async def test_record_calibration_external_requires_provider_name(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 2,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": "pass",
            "calibration_type": "external",
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_record_calibration_external_with_provider_persists_fields(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 2,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": "pass",
            "calibration_type": "external", "provider_name": "Acme Calibration Services",
            "certificate_reference": "CERT-2026-001",
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 200, resp.text

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(cal_token))).json()
    calibration = history["calibrations"][0]
    assert calibration["calibration_type"] == "external"
    assert calibration["provider_name"] == "Acme Calibration Services"
    assert calibration["certificate_reference"] == "CERT-2026-001"


async def test_record_calibration_external_with_provider_supplier_id_derives_name(client, seeded, db):
    """Client gap-analysis Phase 6 (2026-10-05): a known Supplier (role_type "service_provider"/"both")
    can be referenced instead of only free-text provider_name, which is then derived from the supplier's
    legal_name when not also supplied."""
    async with db.begin():
        provider = Supplier(supplier_code="SVC-CAL-1", legal_name="Precision Calibration Services LLC", role_type="service_provider", status="approved")
        db.add(provider)
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 2,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": "pass",
            "calibration_type": "external", "provider_supplier_id": str(provider.id),
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 200, resp.text

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(cal_token))).json()
    calibration = history["calibrations"][0]
    assert calibration["provider_supplier_id"] == str(provider.id)
    assert calibration["provider_name"] == "Precision Calibration Services LLC"


async def test_record_calibration_rejects_provider_supplier_with_wrong_role_type(client, seeded, db):
    async with db.begin():
        provider = Supplier(supplier_code="SUP-WRONG-ROLE-1", legal_name="Just A Material Supplier", role_type="supplier", status="approved")
        db.add(provider)
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 2,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": "pass",
            "calibration_type": "external", "provider_supplier_id": str(provider.id),
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_record_calibration_with_frequency_computes_next_due_date(client, seeded):
    """Client requirement #8: when frequency_days is supplied, the asset's next_calibration_due_date is
    computed from performed_date + frequency_days rather than trusting the caller's own due_date."""
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 2,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": "pass",
            "frequency_days": 90,
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(cal_token))).json()
    # 2026-08-25 + 90 days = 2026-11-23, not the caller's own (much later) due_date.
    assert detail["next_calibration_due_date"] == "2026-11-23"


async def test_calibration_history_captures_standard_and_evidence_fields(client, seeded):
    """EQP-FR-008/EQP-FR-006/EQP-FR-029: calibration standard reference/status/expiry and as-found/
    adjustments/as-left evidence round-trip through GET /equipment/v1/{id}/history."""
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 1,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": "pass",
            "standard_reference": "STD-REF-001", "standard_calibration_status": "current",
            "standard_expiry_date": "2027-06-01",
            "as_found": {"reading": "10.02"}, "adjustments": {"note": "none"}, "as_left": {"reading": "10.00"},
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 200, resp.text

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(cal_token))).json()
    cal = history["calibrations"][0]
    assert cal["standard_reference"] == "STD-REF-001"
    assert cal["standard_calibration_status"] == "current"
    assert cal["standard_expiry_date"] == "2027-06-01"
    assert cal["as_found"] == {"reading": "10.02"}
    assert cal["as_left"] == {"reading": "10.00"}
    assert cal["impact_assessment_required"] is False

    # EQP-FR-013: every mutating command leaves an equipment_use_log trace.
    assert len(history["use_log"]) == 1
    assert history["use_log"][0]["log_type"] == "calibration"


async def test_critical_modification_links_change_control(client, seeded):
    """EQP-FR-022: a critical modification opens a real qms.ChangeControl record through the owning
    qms.change_commands.create_change command (never written directly, AG-05/AG-06) and links it back
    onto the asset. EQP-FR-021: parts_used is captured on the same work order."""
    admin_token = await login(client, "equipment.admin")
    maint_token = await login(client, "maintenance.tech")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 1,
            "type": "planned", "work_performed": "Replaced control board",
            "parts_used": {"parts": [{"part_number": "PN-100", "serial": "SN-9"}]},
            "procedure_version": "PM-PROC-1", "frequency_days": 180, "next_due_date": "2027-02-01",
            "critical_modification": True, "change_classification": "permanent",
            "change_reason": "Control board upgrade",
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(maint_token))).json()
    assert detail["change_control_id"] is not None
    assert detail["next_maintenance_due_date"] == "2027-02-01"

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(maint_token))).json()
    wo = history["maintenance_work_orders"][0]
    assert wo["parts_used"] == {"parts": [{"part_number": "PN-100", "serial": "SN-9"}]}
    assert wo["procedure_version"] == "PM-PROC-1"
    assert wo["frequency_days"] == 180
    assert wo["next_due_date"] == "2027-02-01"


async def test_equipment_use_log_rejects_direct_update(client, db, seeded):
    """EQP-FR-013/029/AG-08: equipment_use_logs is append-only -- migration 0037 grants the app role
    SELECT/INSERT/TRUNCATE only, no UPDATE, enforced at the database privilege level."""
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(admin_token))).json()
    log_id = history["use_log"][0]["id"]

    with pytest.raises(DBAPIError):
        await db.execute(
            EquipmentUseLog.__table__.update().where(EquipmentUseLog.id == uuid.UUID(log_id)).values(log_type="use")
        )
        await db.commit()


async def test_create_asset_unauthenticated_rejected(client, seeded):
    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "equipment_code": "EQP-NOAUTH"},
    )
    assert resp.status_code == 401


async def test_qualify_missing_expected_version_rejected(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/qualifications",
        json={"idempotency_key": idem(), "asset_id": asset_id, "qualification_status": "IQ_COMPLETE", "qualified": False},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    equipment_class_id = await _create_equipment_class(client)
    key = idem()
    payload = {
        "idempotency_key": key, "site_id": str(site_id), "equipment_class_id": equipment_class_id, "is_computer_operated": False,
        "equipment_code": "EQP-IDEM",
    }

    first = await client.post("/equipment/v1/assets", json=payload, headers=auth_headers(admin_token))
    second = await client.post("/equipment/v1/assets", json=payload, headers=auth_headers(admin_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]
    assert first.json()["command_id"] == second.json()["command_id"]


async def test_duplicate_idempotency_key_different_payload_rejected(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    equipment_class_id = await _create_equipment_class(client)
    key = idem()

    resp1 = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": key, "site_id": str(site_id), "equipment_class_id": equipment_class_id, "is_computer_operated": False,
            "equipment_code": "EQP-IDEM-A",
        },
        headers=auth_headers(admin_token),
    )
    assert resp1.status_code == 200
    resp2 = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": key, "site_id": str(site_id), "equipment_class_id": equipment_class_id, "is_computer_operated": False,
            "equipment_code": "EQP-IDEM-B",
        },
        headers=auth_headers(admin_token),
    )
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_dashboard_lists_out_of_service_assets(client, seeded):
    admin_token = await login(client, "equipment.admin")
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    challenge = (
        await client.post(
            f"/equipment/v1/{asset_id}/signature-challenges", json={"action": "hold"}, headers=auth_headers(op_token),
        )
    ).json()
    await _hold(client, op_token, asset_id, expected_version=1, challenge_id=challenge["challenge_id"])

    dashboard = (await client.get("/equipment/v1/dashboard", params={"site_id": str(site_id)}, headers=auth_headers(op_token))).json()
    assert any(a["id"] == asset_id for a in dashboard["out_of_service"])


async def test_return_to_service_rejected_while_dirty(client, seeded):
    """EQP-FR-025 / SG-110 follow-up: Document 39 is now the sole writer of `cleanliness_status`
    (`cleaning_commands._mirror_cleanliness()`); this asserts the cross-module wiring on Document 38's own
    read side (`_ineligibility_reasons()` -> `CLEANING_REQUIRED`)."""
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.releaser")
    eng_token = await login(client, "engineering.manager")
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)

    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    calibration_id = await _latest_calibration_id(client, eng_token, asset_id)
    await _approve_calibration(client, qa_token, asset_id, expected_version=3, calibration_id=calibration_id)

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(op_token))).json()
    assert eligibility["eligible"] is True

    # Starting a cleaning execution against this asset mirrors cleanliness_status to "CLEANING".
    resp = await client.post(
        "/cleaning/v1/executions",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "procedure_version_id": procedure_id,
            "equipment_id": asset_id,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(op_token))).json()
    assert eligibility["eligible"] is False
    assert any(r["code"] == "CLEANING_REQUIRED" for r in eligibility["reasons"])

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=4)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "CLEANING_REQUIRED"


# ---------------------------------------------------------------------------
# CreateEquipmentArea -- added 2026-09-07, project-owner-directed follow-up: EquipmentArea was seed-only
# ("provisioned outside the app today", cleaning_models.py's own docstring), found while building the
# `areaSelect` picker for `/aseptic`'s "Create aseptic operation" form. Same roles as
# equipment_asset.create (Admin + Equipment Administrator).
# ---------------------------------------------------------------------------


async def test_create_area_requires_equipment_administrator_role(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/equipment/v1/areas",
        json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "area_code": "AREA-TEST-NOPERM"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_equipment_administrator_can_create_area_and_it_is_listed(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    resp = await client.post(
        "/equipment/v1/areas",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "area_code": "AREA-TEST-001",
            "area_type": "fill_suite", "classification": "ISO_7", "criticality": "high",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    area_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/equipment/v1/areas/{area_id}", headers=auth_headers(admin_token))).json()
    assert detail["area_code"] == "AREA-TEST-001"
    assert detail["classification"] == "ISO_7"
    assert detail["status"] == "active"

    listing = (await client.get(f"/equipment/v1/areas?q=AREA-TEST-001", headers=auth_headers(admin_token))).json()
    assert any(a["id"] == area_id for a in listing["items"])


async def test_create_area_rejects_duplicate_area_code(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    body = {"idempotency_key": idem(), "site_id": str(site_id), "area_code": "AREA-TEST-002"}
    first = await client.post("/equipment/v1/areas", json=body, headers=auth_headers(admin_token))
    assert first.status_code == 200, first.text

    dup = {**body, "idempotency_key": idem()}
    second = await client.post("/equipment/v1/areas", json=dup, headers=auth_headers(admin_token))
    assert second.status_code == 422, second.text
    assert second.json()["code"] == "VALIDATION_FAILED"


async def test_create_area_unauthenticated_rejected(client, seeded):
    resp = await client.post(
        "/equipment/v1/areas",
        json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "area_code": "AREA-TEST-003"},
    )
    assert resp.status_code == 401


# =======================================================================================================
# Client Topic 14 (SG-112, project-owner-directed): reserve / retire / relocate -- EQP-FR-016/026/027 had
# no operation in Document 38's own declared 9-op API list; the client's own answer is the authorization.
# =======================================================================================================


async def _reserve(client, token, asset_id, batch_id, start_at, end_at, reason=None):
    return await client.post(
        f"/equipment/v1/{asset_id}/reserve",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "batch_id": batch_id,
            "start_at": start_at.isoformat(), "end_at": end_at.isoformat(), "reason": reason,
        },
        headers=auth_headers(token),
    )


async def test_reserve_equipment_shows_batch_user_period_and_prevents_overlap(client, seeded, db):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    async with db.begin():
        batch = await _create_batch(db, seeded, batch_number="BATCH-EQP-RESERVE-1")
    batch_id = str(batch.id)

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    end_at = start_at + timedelta(hours=4)
    resp = await _reserve(client, admin_token, asset_id, batch_id, start_at, end_at, reason="PM batch window")
    assert resp.status_code == 200, resp.text

    history = (await client.get(f"/equipment/v1/{asset_id}/history", headers=auth_headers(admin_token))).json()
    reservations = [u for u in history["use_log"] if u["log_type"] == "reservation"]
    assert len(reservations) == 1
    assert reservations[0]["batch_id"] == batch_id
    assert reservations[0]["operator_user_id"] is not None
    assert reservations[0]["ended_at"] is not None

    # Overlapping window on the same asset is rejected.
    overlap_start = start_at + timedelta(hours=1)
    overlap_end = overlap_start + timedelta(hours=4)
    conflict = await _reserve(client, admin_token, asset_id, batch_id, overlap_start, overlap_end)
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "EQUIPMENT_RESERVATION_CONFLICT"

    # A non-overlapping window after the first reservation ends succeeds.
    later_start = end_at + timedelta(hours=1)
    later_end = later_start + timedelta(hours=2)
    ok = await _reserve(client, admin_token, asset_id, batch_id, later_start, later_end)
    assert ok.status_code == 200, ok.text


async def test_reserve_equipment_rejects_end_before_start(client, seeded, db):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    async with db.begin():
        batch = await _create_batch(db, seeded, batch_number="BATCH-EQP-RESERVE-2")

    start_at = datetime.now(timezone.utc) + timedelta(days=1)
    resp = await _reserve(client, admin_token, asset_id, str(batch.id), start_at, start_at - timedelta(hours=1))
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def _retire(client, token, asset_id, expected_version, challenge_id, reauth_password="ChangeMe123!", reason="End of useful life"):
    return await client.post(
        f"/equipment/v1/{asset_id}/retire",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": expected_version,
            "reason": reason, "challenge_id": challenge_id, "reauth_password": reauth_password,
        },
        headers=auth_headers(token),
    )


async def test_retire_equipment_requires_signature_and_supervisor_role(client, seeded):
    admin_token = await login(client, "equipment.admin")
    supervisor_token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    # Equipment Administrator does not hold equipment_asset.retire at all -- RBAC denies before any
    # signature ceremony is even attempted.
    resp = await client.post(
        f"/equipment/v1/{asset_id}/retire",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 1, "reason": "x",
            "challenge_id": str(uuid.uuid4()), "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"

    # Supervisor holds the permission and the required signing role; missing/wrong signature still
    # blocks it (MISSING_SIGNATURE for a bogus challenge), then a real challenge + password succeeds.
    bogus = await _retire(client, supervisor_token, asset_id, 1, challenge_id=str(uuid.uuid4()), reauth_password="wrong-password")
    assert bogus.status_code in (428, 409)

    challenge = (
        await client.post(
            f"/equipment/v1/{asset_id}/signature-challenges", json={"action": "retire"}, headers=auth_headers(supervisor_token),
        )
    ).json()
    resp = await _retire(client, supervisor_token, asset_id, 1, challenge_id=challenge["challenge_id"])
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(admin_token))).json()
    assert detail["state"] == "RETIRED"

    # Retained historical record, no further mutation possible (same guard every other command path uses).
    challenge2 = (
        await client.post(
            f"/equipment/v1/{asset_id}/signature-challenges", json={"action": "retire"}, headers=auth_headers(supervisor_token),
        )
    ).json()
    resp2 = await _retire(client, supervisor_token, asset_id, 2, challenge_id=challenge2["challenge_id"])
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "INVALID_TRANSITION"


async def _relocate(client, token, asset_id, expected_version, new_location_id, reason=None):
    return await client.post(
        f"/equipment/v1/{asset_id}/relocate",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": expected_version,
            "new_location_id": new_location_id, "reason": reason,
        },
        headers=auth_headers(token),
    )


async def test_relocate_equipment_blocks_use_until_requalified(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert eligibility["eligible"] is True

    resp = await _relocate(client, admin_token, asset_id, expected_version=2, new_location_id=str(uuid.uuid4()), reason="Moved to Suite B")
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}", headers=auth_headers(admin_token))).json()
    assert detail["state"] == "QUALIFICATION_PENDING"
    assert detail["qualification_status"] is None

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert eligibility["eligible"] is False
    assert any(r["code"] == "EQUIPMENT_NOT_QUALIFIED" for r in eligibility["reasons"])

    # A fresh qualification clears it again, same mechanism every other qualification gap already uses.
    await _qualify(client, admin_token, asset_id, expected_version=3, qualified=True)
    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert eligibility["eligible"] is True


async def test_relocate_equipment_requires_permission(client, seeded):
    admin_token = await login(client, "equipment.admin")
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    asset_id = await _create_asset(client, admin_token, site_id)

    resp = await _relocate(client, op_token, asset_id, expected_version=1, new_location_id=str(uuid.uuid4()))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"
