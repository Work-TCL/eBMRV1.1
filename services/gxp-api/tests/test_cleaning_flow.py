"""Document 39 (SPEC-EQP-002) thin slice: create -> complete -> independent verify (the two Document 106
signed actions, rows 109/110), plus line clearance (row 111) and the negative/concurrency/signature cases
the test-case book exercises. Mirrors tests/test_equipment_flow.py's discipline.
"""

import uuid

from tests.conftest import auth_headers, idem, login


async def _create_execution(
    client, token, site_id, procedure_id, equipment_id=None, area_id=None, critical=False,
    sterilization_cycle_id=None, expect_status=200,
):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "procedure_version_id": procedure_id,
        "critical": critical,
    }
    if equipment_id:
        body["equipment_id"] = equipment_id
    if area_id:
        body["area_id"] = area_id
    if sterilization_cycle_id:
        body["sterilization_cycle_id"] = sterilization_cycle_id
    resp = await client.post("/cleaning/v1/executions", json=body, headers=auth_headers(token))
    assert resp.status_code == expect_status, resp.text
    return resp if expect_status != 200 else resp.json()["aggregate_id"]


async def _challenge(client, token, execution_id, action):
    resp = await client.post(
        f"/cleaning/v1/executions/{execution_id}/signature-challenges", json={"action": action}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def _complete(client, token, execution_id, expected_version, previous_batch_identity_removed=True, reason=None, sign=True):
    challenge_id = await _challenge(client, token, execution_id, "complete") if sign else None
    return await client.post(
        f"/cleaning/v1/executions/{execution_id}/complete",
        json={
            "idempotency_key": idem(), "execution_id": execution_id, "expected_version": expected_version,
            "previous_batch_identity_removed": previous_batch_identity_removed, "reason": reason,
            "challenge_id": challenge_id, "reauth_password": "ChangeMe123!" if sign else None,
        },
        headers=auth_headers(token),
    )


async def _verify(client, token, execution_id, expected_version, result, challenge_id):
    return await client.post(
        f"/cleaning/v1/executions/{execution_id}/verify",
        json={
            "idempotency_key": idem(), "execution_id": execution_id, "expected_version": expected_version,
            "result": result, "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(token),
    )


async def test_full_clean_and_independent_verify_flow(client, seeded):
    op_token = await login(client, "sanitation.operator")
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)

    # Bootstrap a fresh equipment asset via the equipment module (no fixture asset in `seeded`).
    admin_token = await login(client, "equipment.admin")
    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-CLN-1"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    equipment_id = resp.json()["aggregate_id"]

    execution_id = await _create_execution(client, op_token, site_id, procedure_id, equipment_id=equipment_id)
    detail = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert detail["state"] == "CLEANING"

    asset_detail = (await client.get(f"/equipment/v1/assets/{equipment_id}")).json()
    assert asset_detail["cleanliness_status"] == "CLEANING"

    resp = await _complete(client, op_token, execution_id, expected_version=1)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert detail["state"] == "CLEANING_VERIFICATION"

    challenge_id = await _challenge(client, qa_token, execution_id, "verify")
    resp = await _verify(client, qa_token, execution_id, expected_version=2, result="pass", challenge_id=challenge_id)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert detail["state"] == "CLEAN"
    assert detail["clean_until"] is not None

    status = (await client.get(f"/cleaning/v1/equipment/{equipment_id}/status")).json()
    assert status["cleanliness_status"] == "CLEAN"

    asset_detail = (await client.get(f"/equipment/v1/assets/{equipment_id}")).json()
    assert asset_detail["cleanliness_status"] == "CLEAN"


async def test_verify_by_performer_rejected(client, seeded):
    # QA Reviewer holds both create/complete and verify permissions here (a QA-performed cleaning is a
    # real scenario), so this exercises the *business-logic* independence check (performer != verifier)
    # rather than being masked by a role-grant denial.
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)

    execution_id = await _create_execution(client, qa_token, site_id, procedure_id, area_id=area_id)
    await _complete(client, qa_token, execution_id, expected_version=1)

    challenge_id = await _challenge(client, qa_token, execution_id, "verify")
    resp = await _verify(client, qa_token, execution_id, expected_version=2, result="pass", challenge_id=challenge_id)
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_failed_verification_holds_and_is_never_overwritten(client, seeded):
    op_token = await login(client, "sanitation.operator")
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)

    execution_id = await _create_execution(client, op_token, site_id, procedure_id, area_id=area_id)
    await _complete(client, op_token, execution_id, expected_version=1)

    challenge_id = await _challenge(client, qa_token, execution_id, "verify")
    resp = await _verify(client, qa_token, execution_id, expected_version=2, result="fail", challenge_id=challenge_id)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert detail["state"] == "HOLD"
    assert detail["requires_deviation"] is True

    # A repeat successful cleaning is a *new* execution -- the original failed record is never edited.
    second_id = await _create_execution(client, op_token, site_id, procedure_id, area_id=area_id)
    assert second_id != execution_id
    first_detail_again = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert first_detail_again["state"] == "HOLD"
    assert first_detail_again["verification_result"] == "fail"


async def test_critical_execution_requires_reason_on_complete(client, seeded):
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-GRADE-A"].id)

    execution_id = await _create_execution(client, op_token, site_id, procedure_id, area_id=area_id, critical=True)
    resp = await _complete(client, op_token, execution_id, expected_version=1, reason=None)
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"

    resp = await _complete(client, op_token, execution_id, expected_version=1, reason="Deep clean per SOP")
    assert resp.status_code == 200, resp.text


async def test_stale_version_rejected(client, seeded):
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)

    execution_id = await _create_execution(client, op_token, site_id, procedure_id, area_id=area_id)
    resp = await _complete(client, op_token, execution_id, expected_version=99)
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_create_execution_requires_role(client, seeded):
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    resp = await client.post(
        "/cleaning/v1/executions",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "procedure_version_id": procedure_id,
            "area_id": str(seeded["areas"]["AREA-WAREHOUSE"].id),
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_create_execution_unauthenticated_rejected(client, seeded):
    resp = await client.post(
        "/cleaning/v1/executions",
        json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "procedure_version_id": str(seeded["cleaning_procedures"]["CLN-PROC-001"].id), "area_id": str(seeded["areas"]["AREA-WAREHOUSE"].id)},
    )
    assert resp.status_code == 401


async def test_line_clearance_full_flow(client, seeded):
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)

    resp = await client.post(
        "/line-clearance/v1",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "area_id": area_id,
            "checklist_version": "LC-1", "items": {"labels_removed": True},
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    clearance_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(f"/line-clearance/v1/{clearance_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/line-clearance/v1/{clearance_id}/complete",
        json={
            "idempotency_key": idem(), "clearance_id": clearance_id, "expected_version": 1, "passed": True,
            "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/line-clearance/v1/{clearance_id}")).json()
    assert detail["state"] == "CLEARED"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded):
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)
    key = idem()
    payload = {"idempotency_key": key, "site_id": str(site_id), "procedure_version_id": procedure_id, "area_id": area_id}

    first = await client.post("/cleaning/v1/executions", json=payload, headers=auth_headers(op_token))
    second = await client.post("/cleaning/v1/executions", json=payload, headers=auth_headers(op_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


# ---------------------------------------------------------------------------
# SG-114 follow-up: CLN-FR-006/010/014/019/025.
# ---------------------------------------------------------------------------


async def test_duplicate_active_cleaning_execution_rejected(client, seeded):
    op_token = await login(client, "sanitation.operator")
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)

    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-CLN-DUP"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    equipment_id = resp.json()["aggregate_id"]

    await _create_execution(client, op_token, site_id, procedure_id, equipment_id=equipment_id)
    resp = await _create_execution(
        client, op_token, site_id, procedure_id, equipment_id=equipment_id, expect_status=422,
    )
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_duplicate_execution_allowed_after_hold(client, seeded):
    # HOLD is deliberately not "active" for CLN-FR-006's guard -- the only way off HOLD is a fresh
    # CreateCleaningExecution attempt (no separate resume-from-hold operation exists in the declared API).
    op_token = await login(client, "sanitation.operator")
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-GRADE-C"].id)

    first_id = await _create_execution(client, op_token, site_id, procedure_id, area_id=area_id)
    await _complete(client, op_token, first_id, expected_version=1)
    challenge_id = await _challenge(client, qa_token, first_id, "verify")
    resp = await _verify(client, qa_token, first_id, expected_version=2, result="fail", challenge_id=challenge_id)
    assert resp.status_code == 200, resp.text

    second_id = await _create_execution(client, op_token, site_id, procedure_id, area_id=area_id)
    assert second_id != first_id


async def test_swab_sample_created_when_procedure_requires_sampling(client, db, seeded):
    from app.modules.equipment.cleaning_models import CleaningProcedureVersion

    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    area_id = str(seeded["areas"]["AREA-GRADE-A"].id)

    procedure = CleaningProcedureVersion(
        site_id=site_id, procedure_number="CLN-PROC-SWAB", version_no=1, cleaning_type="routine",
        state="RELEASED", sample_inspection_requirements={"location": "drain-A"},
    )
    async with db.begin():
        db.add(procedure)
        await db.flush()

    execution_id = await _create_execution(client, op_token, site_id, str(procedure.id), area_id=area_id)
    resp = await _complete(client, op_token, execution_id, expected_version=1)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert detail["swab_sample_id"] is not None


async def test_no_swab_sample_when_procedure_does_not_require_it(client, seeded):
    # CLN-PROC-001 (the default fixture) has no sample_inspection_requirements.
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)

    execution_id = await _create_execution(client, op_token, site_id, procedure_id, area_id=area_id)
    await _complete(client, op_token, execution_id, expected_version=1)
    detail = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert detail["swab_sample_id"] is None


async def test_protection_state_captured_on_complete(client, seeded):
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)

    execution_id = await _create_execution(client, op_token, site_id, procedure_id, area_id=area_id)
    protection_state = {"cover": "closed", "storage": "designated_clean_cart"}
    challenge_id = await _challenge(client, op_token, execution_id, "complete")
    resp = await client.post(
        f"/cleaning/v1/executions/{execution_id}/complete",
        json={
            "idempotency_key": idem(), "execution_id": execution_id, "expected_version": 1,
            "previous_batch_identity_removed": True, "protection_state": protection_state,
            "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert detail["protection_state"] == protection_state


async def test_sterilization_cycle_link_recorded(client, seeded):
    op_token = await login(client, "sanitation.operator")
    admin_token = await login(client, "equipment.admin")
    sterile_token = await login(client, "sterilization.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)

    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-CLN-CIP"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    equipment_id = resp.json()["aggregate_id"]
    # STR-FR-005 follow-up pass: create_process_cycle() now cross-checks equipment eligibility.
    resp = await client.post(
        f"/equipment/v1/{equipment_id}/qualifications",
        json={
            "idempotency_key": idem(), "asset_id": equipment_id, "expected_version": 1,
            "qualification_status": "qualified", "qualified": True,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/sterilization/v1/cycles",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "process_type": "CIP", "equipment_id": equipment_id,
            "profile_version_id": str(seeded["sterilization_profile"].id),
            "load_items": [{"item_type": "line", "item_reference": "CIP-SKID-1"}],
        },
        headers=auth_headers(sterile_token),
    )
    assert resp.status_code == 200, resp.text
    cycle_id = resp.json()["aggregate_id"]

    execution_id = await _create_execution(
        client, op_token, site_id, procedure_id, equipment_id=equipment_id, sterilization_cycle_id=cycle_id,
    )
    detail = (await client.get(f"/cleaning/v1/executions/{execution_id}")).json()
    assert detail["sterilization_cycle_id"] == cycle_id


async def test_sterilization_cycle_link_rejects_unknown_cycle(client, seeded):
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)

    resp = await _create_execution(
        client, op_token, site_id, procedure_id, area_id=area_id,
        sterilization_cycle_id=str(uuid.uuid4()), expect_status=404,
    )
    assert resp.json()["code"] == "NOT_FOUND"


async def test_line_clearance_wrong_equipment_installed_rejected(client, seeded):
    # A freshly created asset has no qualification yet -- get_eligibility() correctly reports ineligible.
    op_token = await login(client, "sanitation.operator")
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]

    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-LC-BAD"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    equipment_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/line-clearance/v1",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "area_id": str(seeded["areas"]["AREA-WAREHOUSE"].id),
            "checklist_version": "LC-1", "items": [{"item_type": "equipment", "equipment_id": equipment_id}],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    clearance_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(f"/line-clearance/v1/{clearance_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/line-clearance/v1/{clearance_id}/complete",
        json={
            "idempotency_key": idem(), "clearance_id": clearance_id, "expected_version": 1, "passed": True,
            "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "WRONG_EQUIPMENT_INSTALLED"
    detail = (await client.get(f"/line-clearance/v1/{clearance_id}")).json()
    assert detail["state"] == "IN_PROGRESS"


async def test_line_clearance_eligible_equipment_installed_passes(client, seeded):
    op_token = await login(client, "sanitation.operator")
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    procedure_id = str(seeded["cleaning_procedures"]["CLN-PROC-001"].id)

    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-LC-GOOD"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    equipment_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/equipment/v1/{equipment_id}/qualifications",
        json={
            "idempotency_key": idem(), "asset_id": equipment_id, "expected_version": 1,
            "qualification_status": "PQ_COMPLETE", "qualified": True,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/equipment/v1/{equipment_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": equipment_id, "expected_version": 2,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": "pass",
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 200, resp.text

    # Clean the equipment (create -> complete -> pass verify) so cleanliness_status reaches CLEAN.
    execution_id = await _create_execution(client, op_token, site_id, procedure_id, equipment_id=equipment_id)
    await _complete(client, op_token, execution_id, expected_version=1)
    challenge_id = await _challenge(client, qa_token, execution_id, "verify")
    resp = await _verify(client, qa_token, execution_id, expected_version=2, result="pass", challenge_id=challenge_id)
    assert resp.status_code == 200, resp.text

    eligibility = (await client.get(f"/equipment/v1/{equipment_id}/eligibility")).json()
    assert eligibility["eligible"] is True

    resp = await client.post(
        "/line-clearance/v1",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "area_id": str(seeded["areas"]["AREA-WAREHOUSE"].id),
            "checklist_version": "LC-1", "items": [{"item_type": "equipment", "equipment_id": equipment_id}],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    clearance_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(f"/line-clearance/v1/{clearance_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/line-clearance/v1/{clearance_id}/complete",
        json={
            "idempotency_key": idem(), "clearance_id": clearance_id, "expected_version": 1, "passed": True,
            "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/line-clearance/v1/{clearance_id}")).json()
    assert detail["state"] == "CLEARED"


async def test_line_clearance_non_equipment_items_untouched(client, seeded):
    # Backward compatibility: a dict-shaped (not list) items payload -- the pre-existing convention used
    # by test_line_clearance_full_flow -- must still pass through untouched (no crash, no false rejection).
    op_token = await login(client, "sanitation.operator")
    site_id = seeded["site_id"]
    area_id = str(seeded["areas"]["AREA-WAREHOUSE"].id)

    resp = await client.post(
        "/line-clearance/v1",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "area_id": area_id,
            "checklist_version": "LC-1", "items": {"labels_removed": True},
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    clearance_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(f"/line-clearance/v1/{clearance_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/line-clearance/v1/{clearance_id}/complete",
        json={
            "idempotency_key": idem(), "clearance_id": clearance_id, "expected_version": 1, "passed": True,
            "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
