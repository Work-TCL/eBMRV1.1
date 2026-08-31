"""Document 41 (SPEC-EQP-004) thin slice: create task -> collect -> record result -> independent review
(Document 106 rows 114/115), action-limit excursion auto-creation, and area readiness (the Document 40
cross-module payoff). Mirrors tests/test_cleaning_flow.py's discipline.
"""

from tests.conftest import auth_headers, idem, login


async def _create_task(client, token, site_id, program_id, location_id):
    resp = await client.post(
        "/em/v1/tasks",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "program_version_id": program_id,
            "location_id": location_id, "monitoring_type": "viable_air",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _collect(client, token, sample_id, expected_version):
    return await client.post(
        f"/em/v1/tasks/{sample_id}/collect",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": expected_version, "instrument_or_media_ref": {"media_lot": "M-1"}},
        headers=auth_headers(token),
    )


async def _challenge(client, token, sample_id, action):
    resp = await client.post(f"/em/v1/results/{sample_id}/signature-challenges", json={"action": action}, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def _record_result(client, token, sample_id, expected_version, alert_action_status, result=None):
    challenge_id = await _challenge(client, token, sample_id, "record_result")
    return await client.post(
        "/em/v1/results",
        json={
            "idempotency_key": idem(), "sample_id": sample_id, "expected_version": expected_version,
            "result": result or {"cfu": 1}, "alert_action_status": alert_action_status,
            "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(token),
    )


async def _review(client, token, sample_id, expected_version):
    challenge_id = await _challenge(client, token, sample_id, "review")
    return await client.post(
        f"/em/v1/results/{sample_id}/review",
        json={
            "idempotency_key": idem(), "sample_id": sample_id, "expected_version": expected_version,
            "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(token),
    )


async def test_create_program_via_api(client, seeded):
    em_token = await login(client, "em.technician")
    site_id = seeded["site_id"]
    resp = await client.post(
        "/em/v1/programs",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "program_number": "EM-PROG-API-1",
            "monitoring_types": {"types": ["temperature", "humidity"]},
            "alert_limits": {"temperature": 25}, "action_limits": {"temperature": 30},
        },
        headers=auth_headers(em_token),
    )
    assert resp.status_code == 200, resp.text


async def test_full_sample_collect_result_review_flow(client, seeded):
    em_token = await login(client, "em.technician")
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    program_id = str(seeded["em_program"].id)
    location_id = str(seeded["em_locations"]["EM-LOC-GRADE-A-01"].id)

    sample_id = await _create_task(client, em_token, site_id, program_id, location_id)
    resp = await _collect(client, em_token, sample_id, expected_version=1)
    assert resp.status_code == 200, resp.text

    resp = await _record_result(client, em_token, sample_id, expected_version=2, alert_action_status="normal")
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/em/v1/results/{sample_id}")).json()
    assert detail["state"] == "RESULT_PENDING"
    assert detail["alert_action_status"] == "normal"

    resp = await _review(client, qa_token, sample_id, expected_version=3)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/em/v1/results/{sample_id}")).json()
    assert detail["state"] == "REVIEWED"


async def test_review_by_performer_rejected(client, seeded):
    em_token = await login(client, "em.technician")
    site_id = seeded["site_id"]
    program_id = str(seeded["em_program"].id)
    location_id = str(seeded["em_locations"]["EM-LOC-GRADE-C-01"].id)

    sample_id = await _create_task(client, em_token, site_id, program_id, location_id)
    await _collect(client, em_token, sample_id, expected_version=1)
    await _record_result(client, em_token, sample_id, expected_version=2, alert_action_status="normal")

    resp = await _review(client, em_token, sample_id, expected_version=3)
    assert resp.status_code == 403  # em.technician has no em_sample.review grant


async def test_action_excursion_auto_creates_excursion_and_blocks_area_readiness(client, seeded):
    em_token = await login(client, "em.technician")
    site_id = seeded["site_id"]
    program_id = str(seeded["em_program"].id)
    location = seeded["em_locations"]["EM-LOC-GRADE-A-01"]
    area_id = str(seeded["areas"]["AREA-GRADE-A"].id)

    readiness = (await client.get(f"/em/v1/areas/{area_id}/readiness")).json()
    assert readiness["status"] == "READY"

    sample_id = await _create_task(client, em_token, site_id, program_id, str(location.id))
    await _collect(client, em_token, sample_id, expected_version=1)
    resp = await _record_result(client, em_token, sample_id, expected_version=2, alert_action_status="action_excursion", result={"cfu": 999})
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/em/v1/results/{sample_id}")).json()
    assert detail["requires_deviation"] is True

    readiness = (await client.get(f"/em/v1/areas/{area_id}/readiness")).json()
    assert readiness["status"] == "HOLD"
    assert readiness["ready"] is False
    assert readiness["open_excursion_count"] == 1


async def test_stale_version_rejected(client, seeded):
    em_token = await login(client, "em.technician")
    site_id = seeded["site_id"]
    program_id = str(seeded["em_program"].id)
    location_id = str(seeded["em_locations"]["EM-LOC-GRADE-C-01"].id)

    sample_id = await _create_task(client, em_token, site_id, program_id, location_id)
    resp = await _collect(client, em_token, sample_id, expected_version=99)
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_create_task_requires_role(client, seeded):
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    resp = await client.post(
        "/em/v1/tasks",
        json={
            "idempotency_key": idem(), "site_id": str(site_id),
            "program_version_id": str(seeded["em_program"].id),
            "location_id": str(seeded["em_locations"]["EM-LOC-GRADE-C-01"].id), "monitoring_type": "viable_air",
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_create_task_unauthenticated_rejected(client, seeded):
    resp = await client.post(
        "/em/v1/tasks",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]),
            "program_version_id": str(seeded["em_program"].id),
            "location_id": str(seeded["em_locations"]["EM-LOC-GRADE-C-01"].id), "monitoring_type": "viable_air",
        },
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# SG-115 follow-up: EM-FR-006/007/009.
# ---------------------------------------------------------------------------


async def test_collect_rejects_ineligible_instrument(client, seeded):
    em_token = await login(client, "em.technician")
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    program_id = str(seeded["em_program"].id)
    location_id = str(seeded["em_locations"]["EM-LOC-GRADE-A-01"].id)

    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-EM-UNQUAL"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    instrument_id = resp.json()["aggregate_id"]

    sample_id = await _create_task(client, em_token, site_id, program_id, location_id)
    resp = await client.post(
        f"/em/v1/tasks/{sample_id}/collect",
        json={
            "idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1,
            "instrument_equipment_id": instrument_id,
        },
        headers=auth_headers(em_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "EM_INSTRUMENT_INELIGIBLE"


async def test_collect_accepts_eligible_instrument_and_captures_media_reagent(client, seeded):
    em_token = await login(client, "em.technician")
    admin_token = await login(client, "equipment.admin")
    cal_token = await login(client, "calibration.tech")
    site_id = seeded["site_id"]
    program_id = str(seeded["em_program"].id)
    location_id = str(seeded["em_locations"]["EM-LOC-GRADE-A-01"].id)

    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-EM-QUAL"},
        headers=auth_headers(admin_token),
    )
    instrument_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/equipment/v1/{instrument_id}/qualifications",
        json={
            "idempotency_key": idem(), "asset_id": instrument_id, "expected_version": 1,
            "qualification_status": "qualified", "qualified": True,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/equipment/v1/{instrument_id}/calibrations",
        json={
            "idempotency_key": idem(), "asset_id": instrument_id, "expected_version": 2,
            "due_date": "2027-01-01", "performed_date": "2026-08-25", "result": "pass",
        },
        headers=auth_headers(cal_token),
    )
    assert resp.status_code == 200, resp.text

    sample_id = await _create_task(client, em_token, site_id, program_id, location_id)
    media_reagent_ref = {"media_lot": "TSA-2026-01", "growth_promotion": "pass"}
    resp = await client.post(
        f"/em/v1/tasks/{sample_id}/collect",
        json={
            "idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1,
            "instrument_equipment_id": instrument_id, "media_reagent_ref": media_reagent_ref,
        },
        headers=auth_headers(em_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/em/v1/results/{sample_id}")).json()
    assert detail["media_reagent_ref"] == media_reagent_ref


async def test_incubation_conditions_captured_on_result(client, seeded):
    em_token = await login(client, "em.technician")
    site_id = seeded["site_id"]
    program_id = str(seeded["em_program"].id)
    location_id = str(seeded["em_locations"]["EM-LOC-GRADE-C-01"].id)

    sample_id = await _create_task(client, em_token, site_id, program_id, location_id)
    await _collect(client, em_token, sample_id, expected_version=1)
    incubation_conditions = {"temperature_c": 32.5, "duration_hours": 48}
    challenge_id = await _challenge(client, em_token, sample_id, "record_result")
    resp = await client.post(
        "/em/v1/results",
        json={
            "idempotency_key": idem(), "sample_id": sample_id, "expected_version": 2,
            "result": {"cfu": 1}, "alert_action_status": "normal", "incubation_conditions": incubation_conditions,
            "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(em_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/em/v1/results/{sample_id}")).json()
    assert detail["incubation_conditions"] == incubation_conditions


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded):
    em_token = await login(client, "em.technician")
    site_id = seeded["site_id"]
    key = idem()
    payload = {
        "idempotency_key": key, "site_id": str(site_id), "program_version_id": str(seeded["em_program"].id),
        "location_id": str(seeded["em_locations"]["EM-LOC-GRADE-C-01"].id), "monitoring_type": "viable_air",
    }
    first = await client.post("/em/v1/tasks", json=payload, headers=auth_headers(em_token))
    second = await client.post("/em/v1/tasks", json=payload, headers=auth_headers(em_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]
