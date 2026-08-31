"""Document 38 (SPEC-EQP-001) thin slice: create -> qualify -> calibrate -> return-to-service (the one
place QUALIFIED_AVAILABLE is ever written), plus the negative/concurrency/signature cases the test-case
book (test-cases/WP-06/Document_38_SPEC-EQP-001_TEST_CASES.md) exercises. Mirrors the discipline used in
tests/test_material_flow.py.
"""

import uuid

import pytest
from sqlalchemy.exc import DBAPIError

from app.modules.equipment.models import EquipmentUseLog
from tests.conftest import auth_headers, idem, login


async def _create_asset(client, token, site_id, equipment_code="EQP-1"):
    resp = await client.post(
        "/equipment/v1/assets",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "equipment_code": equipment_code,
            "manufacturer": "Acme", "model": "M1", "serial_no": "SN-1",
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

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
    assert detail["state"] == "INSTALLED"
    assert detail["version"] == 1


async def test_create_asset_requires_equipment_administrator_role(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "equipment_code": "EQP-X"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_full_qualify_calibrate_return_to_service_flow(client, seeded):
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    receipt = await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    assert receipt["resulting_version"] == 2

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
    assert detail["state"] == "VERIFICATION"
    assert detail["qualification_status"] == "QUALIFIED"

    receipt = await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    assert receipt["resulting_version"] == 3
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
    assert detail["calibration_status"] == "current"

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility")).json()
    assert eligibility["eligible"] is True
    assert eligibility["reasons"] == []

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=3)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
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
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
    assert detail["state"] == "OUT_OF_SERVICE"
    assert detail["hold_flag"] is True
    assert detail["calibration_status"] == "oot"

    history = (await client.get(f"/equipment/v1/{asset_id}/history")).json()
    assert history["calibrations"][0]["impact_assessment_required"] is True

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility")).json()
    assert eligibility["eligible"] is False
    assert any(r["code"] == "CALIBRATION_OOT_IMPACT_REQUIRED" for r in eligibility["reasons"])

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=3)
    assert resp.status_code == 409
    assert resp.json()["code"] == "CALIBRATION_OOT_IMPACT_REQUIRED"

    # A subsequent passing calibration clears the hold and allows return to service.
    receipt = await _calibrate(client, cal_token, asset_id, expected_version=3, result="pass")
    assert receipt["resulting_version"] == 4
    resp = await _return_to_service(client, eng_token, asset_id, expected_version=4)
    assert resp.status_code == 200, resp.text


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
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
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
    maint_token = await login(client, "maintenance.tech")
    eng_token = await login(client, "engineering.manager")
    site_id = seeded["site_id"]

    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")
    await _return_to_service(client, eng_token, asset_id, expected_version=3)

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 4,
            "type": "corrective", "fault_description": "Motor stall",
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
    assert detail["state"] == "OUT_OF_SERVICE"
    assert detail["hold_flag"] is True

    history = (await client.get(f"/equipment/v1/{asset_id}/history")).json()
    wo_id = history["maintenance_work_orders"][0]["id"]

    resp = await client.post(
        f"/equipment/v1/{asset_id}/maintenance",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 5,
            "work_order_id": wo_id, "work_performed": "Replaced motor", "verified": True,
        },
        headers=auth_headers(maint_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
    assert detail["state"] == "VERIFICATION"
    assert detail["maintenance_status"] == "complete"

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=6)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
    assert detail["state"] == "QUALIFIED_AVAILABLE"


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

    history = (await client.get(f"/equipment/v1/{asset_id}/history")).json()
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

    detail = (await client.get(f"/equipment/v1/assets/{asset_id}")).json()
    assert detail["change_control_id"] is not None
    assert detail["next_maintenance_due_date"] == "2027-02-01"

    history = (await client.get(f"/equipment/v1/{asset_id}/history")).json()
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

    history = (await client.get(f"/equipment/v1/{asset_id}/history")).json()
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
    key = idem()
    payload = {"idempotency_key": key, "site_id": str(site_id), "equipment_code": "EQP-IDEM"}

    first = await client.post("/equipment/v1/assets", json=payload, headers=auth_headers(admin_token))
    second = await client.post("/equipment/v1/assets", json=payload, headers=auth_headers(admin_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]
    assert first.json()["command_id"] == second.json()["command_id"]


async def test_duplicate_idempotency_key_different_payload_rejected(client, seeded):
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    key = idem()

    resp1 = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": key, "site_id": str(site_id), "equipment_code": "EQP-IDEM-A"},
        headers=auth_headers(admin_token),
    )
    assert resp1.status_code == 200
    resp2 = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": key, "site_id": str(site_id), "equipment_code": "EQP-IDEM-B"},
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

    dashboard = (await client.get("/equipment/v1/dashboard", params={"site_id": str(site_id)})).json()
    assert any(a["id"] == asset_id for a in dashboard["out_of_service"])


async def test_return_to_service_rejected_while_dirty(client, seeded):
    """EQP-FR-025 / SG-110 follow-up: Document 39 is now the sole writer of `cleanliness_status`
    (`cleaning_commands._mirror_cleanliness()`); this asserts the cross-module wiring on Document 38's own
    read side (`_ineligibility_reasons()` -> `CLEANING_REQUIRED`)."""
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    eng_token = await login(client, "engineering.manager")
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)

    asset_id = await _create_asset(client, admin_token, site_id)
    await _qualify(client, admin_token, asset_id, expected_version=1, qualified=True)
    await _calibrate(client, cal_token, asset_id, expected_version=2, result="pass")

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility")).json()
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

    eligibility = (await client.get(f"/equipment/v1/{asset_id}/eligibility")).json()
    assert eligibility["eligible"] is False
    assert any(r["code"] == "CLEANING_REQUIRED" for r in eligibility["reasons"])

    resp = await _return_to_service(client, eng_token, asset_id, expected_version=3)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "CLEANING_REQUIRED"
