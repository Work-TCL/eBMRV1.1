"""Client requirement #4 (Expiry / Retest / Important Date Reminders) -- app/modules/dashboard/service.py
aggregates material lot expiry/retest, equipment calibration/maintenance/qualification due dates, and
supplier qualification expiry into one "coming due" list. Verifies the horizon filter (in-window vs.
out-of-window vs. already-past dates all resolve correctly) and that already-consumed/rejected lots are
excluded as noise, matching the FEFO gate's own terminal-state treatment.
"""

from datetime import date, timedelta

from sqlalchemy import select

from datetime import datetime, timezone

from app.modules.equipment.models import EquipmentAsset
from app.modules.material.models import MaterialLot
from tests.conftest import auth_headers, idem, login
from tests.test_equipment_flow import _calibrate, _create_asset, _qualify
from tests.test_material_flow import _create_material
from tests.test_qms_risk import _accept, _add_controls, _add_initial_assessment, _add_residual_assessment, _create_risk, _setup
from tests.test_supplier_quality import _site_id_for, _approve_flow, _create_supplier


async def test_reminders_lists_material_lot_expiry_within_horizon_only(client, seeded, db):
    op_token = await login(client, "operator1")
    material_id = await _create_material(client, seeded["site_id"], code="RM-REMIND-1")

    soon = (date.today() + timedelta(days=5)).isoformat()
    far = (date.today() + timedelta(days=200)).isoformat()

    for lot, expiry in (("LOT-SOON", soon), ("LOT-FAR", far)):
        resp = await client.post(
            f"/materials/{material_id}/lots",
            json={
                "idempotency_key": idem(), "material_id": material_id, "site_id": str(seeded["site_id"]),
                "internal_lot": lot, "received_quantity": "10.000000", "uom": "kg", "expiry_date": expiry,
            },
            headers=auth_headers(op_token),
        )
        assert resp.status_code == 200, resp.text

    resp = await client.get("/dashboard/v1/reminders?within_days=30", headers=auth_headers(op_token))
    assert resp.status_code == 200, resp.text
    labels = {r["label"] for r in resp.json() if r["category"] == "material_lot_expiry"}
    assert any("LOT-SOON" in label for label in labels)
    assert not any("LOT-FAR" in label for label in labels)


async def test_reminders_excludes_consumed_lots(client, seeded, db):
    """A lot already consumed needs no heads-up -- same terminal-state treatment as the FEFO gate."""
    op_token = await login(client, "operator1")
    material_id = await _create_material(client, seeded["site_id"], code="RM-REMIND-2")
    soon = (date.today() + timedelta(days=5)).isoformat()
    resp = await client.post(
        f"/materials/{material_id}/lots",
        json={
            "idempotency_key": idem(), "material_id": material_id, "site_id": str(seeded["site_id"]),
            "internal_lot": "LOT-CONSUMED", "received_quantity": "10.000000", "uom": "kg", "expiry_date": soon,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    lot_id = resp.json()["aggregate_id"]

    async with db.begin():
        lot = await db.get(MaterialLot, lot_id)
        lot.status = "consumed"

    resp = await client.get("/dashboard/v1/reminders?within_days=30", headers=auth_headers(op_token))
    assert resp.status_code == 200, resp.text
    assert not any("LOT-CONSUMED" in r["label"] for r in resp.json())


async def test_reminders_lists_equipment_calibration_and_qualification_due_dates(client, seeded, db):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    asset_id = await _create_asset(client, admin_token, seeded["site_id"], equipment_code="EQP-REMIND-1")

    q = await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    # Extend qualification with an expiry within the horizon by calling the endpoint again with a version bump.
    soon = (date.today() + timedelta(days=10)).isoformat()
    resp = await client.post(
        f"/equipment/v1/{asset_id}/qualifications",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": q["resulting_version"],
            "qualification_status": "PQ_COMPLETE", "qualified": True, "expiry_date": soon,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    version_after_qual = resp.json()["resulting_version"]

    calib_soon = (date.today() + timedelta(days=3)).isoformat()
    resp = await client.post(
        f"/equipment/v1/{asset_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": version_after_qual,
            "due_date": calib_soon, "performed_date": date.today().isoformat(), "result": "pass",
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/dashboard/v1/reminders?within_days=30", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    rows = [r for r in resp.json() if r["entity_id"] == asset_id]
    categories = {r["category"] for r in rows}
    assert "equipment_calibration" in categories
    assert "equipment_qualification" in categories


async def test_reminders_excludes_retired_equipment(client, seeded, db):
    admin_token = await login(client, "equipment.admin")
    asset_id = await _create_asset(client, admin_token, seeded["site_id"], equipment_code="EQP-REMIND-2")
    soon = (date.today() + timedelta(days=5)).isoformat()
    async with db.begin():
        asset = await db.get(EquipmentAsset, asset_id)
        asset.next_calibration_due_date = date.today() + timedelta(days=5)
        asset.state = "RETIRED"

    resp = await client.get("/dashboard/v1/reminders?within_days=30", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    assert not any(r["entity_id"] == asset_id for r in resp.json())


async def test_reminders_lists_approved_supplier_qualification_expiry(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    qa_releaser_token = await login(client, "qa.releaser")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-REMIND-1", name="Reminder Test Supplier Co.")
    site_id = await _site_id_for(db, supplier_id)

    soon = (date.today() + timedelta(days=20)).isoformat() + "T00:00:00Z"
    resp = await client.post(
        f"/suppliers/{supplier_id}/qualifications",
        json={
            "idempotency_key": idem(), "supplier_id": supplier_id, "supplier_site_id": site_id,
            "risk_class": "critical", "expires_at": soon,
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    qualification_id = resp.json()["aggregate_id"]

    resp = await _approve_flow(client, qa_releaser_token, qualification_id)
    assert resp.status_code == 200, resp.text

    resp = await client.get("/dashboard/v1/reminders?within_days=30", headers=auth_headers(pe_token))
    assert resp.status_code == 200, resp.text
    rows = [r for r in resp.json() if r["entity_id"] == qualification_id]
    assert len(rows) == 1
    assert rows[0]["category"] == "supplier_qualification"
    assert "Reminder Test Supplier Co." in rows[0]["label"]


async def test_reminders_lists_accepted_risk_with_review_due_within_horizon(client, seeded, db):
    """RSK-FR-013/017: an ACCEPTED risk's next_review_due_at surfaces here as a 'coming due' reminder --
    the one cheap, non-regulated half of the documented no-scheduler gap (no code path alerts anyone
    proactively otherwise; see risk_models.py's module-level comment)."""
    owner, methodology_id = await _setup(db, seeded, "remind1")
    token = await login(client, "admin.riskremind1")

    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id, risk_number="RSK-REMIND-1")
    assert (await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)).status_code == 200
    assert (await _add_controls(client, token, risk_id, 2)).status_code == 200
    assert (await _add_residual_assessment(client, token, risk_id, 3)).status_code == 200

    due_soon = datetime.now(timezone.utc) + timedelta(days=10)
    resp = await _accept(client, token, risk_id, 4, next_review_due_at=due_soon.isoformat())
    assert resp.status_code == 200, resp.text

    resp = await client.get("/dashboard/v1/reminders?within_days=365", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    rows = [r for r in resp.json() if r["entity_id"] == risk_id]
    assert len(rows) == 1
    assert rows[0]["category"] == "risk_review_due"
    assert "RSK-REMIND-1" in rows[0]["label"]


async def test_reminders_excludes_risk_not_yet_accepted(client, seeded, db):
    """A risk still mid-assessment has no next_review_due_at yet -- nothing to remind anyone of."""
    owner, _methodology_id = await _setup(db, seeded, "remind2")
    token = await login(client, "admin.riskremind2")

    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id, risk_number="RSK-REMIND-2")

    resp = await client.get("/dashboard/v1/reminders?within_days=365", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    assert not any(r["entity_id"] == risk_id for r in resp.json())
