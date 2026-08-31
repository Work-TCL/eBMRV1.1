"""Document 42 (SPEC-EQP-005) thin slice: create cycle -> start -> record data -> independent review
(Document 106 rows 118/117), critical-alarm auto-hold, and filter install -> integrity tests -> complete
(row 116). Mirrors tests/test_cleaning_flow.py's discipline.
"""

import uuid

from sqlalchemy import select

from app.modules.equipment.sterilization_models import SterilizationLoadItem
from tests.conftest import auth_headers, idem, login


async def _create_equipment(client, _token_unused, site_id, code="EQP-STR-1"):
    # equipment_asset.create is granted only to Equipment Administrator (Document 38) -- not to
    # Sterilization Operator/QA Reviewer -- so asset bootstrap always uses that role regardless of which
    # actor the rest of the test uses. Qualified here (STR-FR-005 follow-up pass: create_process_cycle()
    # now cross-checks equipment eligibility) -- same qualify call test_aseptic_flow's own
    # _create_and_qualify_equipment already uses successfully.
    admin_token = await login(client, "equipment.admin")
    resp = await client.post(
        "/equipment/v1/assets", json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": code},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    asset_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/equipment/v1/{asset_id}/qualifications",
        json={
            "idempotency_key": idem(), "asset_id": asset_id, "expected_version": 1,
            "qualification_status": "qualified", "qualified": True,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return asset_id


async def _create_cycle(client, token, site_id, equipment_id, profile_id, process_type="steam_autoclave"):
    resp = await client.post(
        "/sterilization/v1/cycles",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "process_type": process_type,
            "equipment_id": equipment_id, "profile_version_id": profile_id,
            "load_items": [{"item_type": "component", "item_reference": "COMP-1"}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _cycle_challenge(client, token, cycle_id, action):
    resp = await client.post(f"/sterilization/v1/cycles/{cycle_id}/signature-challenges", json={"action": action}, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def _start(client, token, cycle_id, expected_version):
    challenge_id = await _cycle_challenge(client, token, cycle_id, "start")
    return await client.post(
        f"/sterilization/v1/cycles/{cycle_id}/start",
        json={"idempotency_key": idem(), "cycle_id": cycle_id, "expected_version": expected_version, "challenge_id": challenge_id, "reauth_password": "ChangeMe123!"},
        headers=auth_headers(token),
    )


async def _record_data(client, token, cycle_id, expected_version, final=False, critical_alarm=False):
    return await client.post(
        f"/sterilization/v1/cycles/{cycle_id}/data",
        json={
            "idempotency_key": idem(), "cycle_id": cycle_id, "expected_version": expected_version,
            "parameter_data": {"temperature": 121}, "final": final, "critical_alarm": critical_alarm,
        },
        headers=auth_headers(token),
    )


async def _review(client, token, cycle_id, expected_version, decision, reason=None):
    challenge_id = await _cycle_challenge(client, token, cycle_id, "review")
    return await client.post(
        f"/sterilization/v1/cycles/{cycle_id}/review",
        json={
            "idempotency_key": idem(), "cycle_id": cycle_id, "expected_version": expected_version,
            "decision": decision, "reason": reason, "challenge_id": challenge_id, "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(token),
    )


async def test_full_cycle_lifecycle_accepted_issues_sterile_status(client, seeded, db):
    op_token = await login(client, "sterilization.operator")
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    profile_id = str(seeded["sterilization_profile"].id)

    equipment_id = await _create_equipment(client, op_token, site_id)
    cycle_id = await _create_cycle(client, op_token, site_id, equipment_id, profile_id)

    resp = await _start(client, op_token, cycle_id, expected_version=1)
    assert resp.status_code == 200, resp.text

    resp = await _record_data(client, op_token, cycle_id, expected_version=2, final=True)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/sterilization/v1/cycles/{cycle_id}")).json()
    assert detail["state"] == "REVIEW_PENDING"

    resp = await _review(client, qa_token, cycle_id, expected_version=3, decision="accept")
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/sterilization/v1/cycles/{cycle_id}")).json()
    assert detail["state"] == "ACCEPTED"

    # STR-FR-012: acceptance issues sterile status onto every load item, with an expiry from the
    # profile's sterile_status_validity_hours.
    items = (
        await db.execute(select(SterilizationLoadItem).where(SterilizationLoadItem.cycle_id == uuid.UUID(cycle_id)))
    ).scalars().all()
    assert len(items) == 1
    assert items[0].sterile_status == "eligible"
    assert items[0].sterile_status_expiry is not None

    status = (await client.get(f"/sterilization/v1/items/{items[0].id}/status")).json()
    assert status["sterile_status"] == "eligible"


async def test_critical_alarm_holds_and_blocks_acceptance(client, seeded):
    op_token = await login(client, "sterilization.operator")
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    profile_id = str(seeded["sterilization_profile"].id)

    equipment_id = await _create_equipment(client, op_token, site_id, code="EQP-STR-2")
    cycle_id = await _create_cycle(client, op_token, site_id, equipment_id, profile_id)
    await _start(client, op_token, cycle_id, expected_version=1)

    resp = await _record_data(client, op_token, cycle_id, expected_version=2, critical_alarm=True)
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/sterilization/v1/cycles/{cycle_id}")).json()
    assert detail["state"] == "HOLD"
    assert detail["requires_deviation"] is True

    resp = await _review(client, qa_token, cycle_id, expected_version=3, decision="accept")
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"

    resp = await _review(client, qa_token, cycle_id, expected_version=3, decision="reject", reason="Critical alarm during cycle")
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/sterilization/v1/cycles/{cycle_id}")).json()
    assert detail["state"] == "FAILED"


async def test_review_by_starter_rejected(client, seeded):
    # QA Reviewer holds both create/start and review permissions here (a QA-performed cycle start is a
    # real scenario, same precedent as test_cleaning_flow's test_verify_by_performer_rejected), so this
    # exercises the *business-logic* independence check rather than being masked by a role-grant denial.
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    profile_id = str(seeded["sterilization_profile"].id)

    equipment_id = await _create_equipment(client, qa_token, site_id, code="EQP-STR-3")
    cycle_id = await _create_cycle(client, qa_token, site_id, equipment_id, profile_id)
    await _start(client, qa_token, cycle_id, expected_version=1)
    await _record_data(client, qa_token, cycle_id, expected_version=2, final=True)

    resp = await _review(client, qa_token, cycle_id, expected_version=3, decision="accept")
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_filter_install_integrity_and_complete_flow(client, seeded):
    op_token = await login(client, "sterilization.operator")
    site_id = seeded["site_id"]

    resp = await client.post(
        "/filtration/v1/filters/install",
        json={"idempotency_key": idem(), "site_id": str(site_id), "filter_serial": "FLT-001"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    use_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/filtration/v1/filters/{use_id}/integrity-tests",
        json={"idempotency_key": idem(), "use_id": use_id, "expected_version": 1, "phase": "pre", "result": "pass"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/filtration/v1/filters/{use_id}/integrity-tests",
        json={"idempotency_key": idem(), "use_id": use_id, "expected_version": 2, "phase": "post", "result": "pass"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    challenge = (
        await client.post(f"/filtration/v1/uses/{use_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/filtration/v1/uses/{use_id}/complete",
        json={
            "idempotency_key": idem(), "use_id": use_id, "expected_version": 3,
            "process_parameters": {"pressure": 2.1}, "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/filtration/v1/filters/{use_id}")).json()
    assert detail["state"] == "ACCEPTED"


async def test_filter_pre_use_integrity_failure_holds_filter(client, seeded):
    op_token = await login(client, "sterilization.operator")
    site_id = seeded["site_id"]

    resp = await client.post(
        "/filtration/v1/filters/install",
        json={"idempotency_key": idem(), "site_id": str(site_id), "filter_serial": "FLT-002"},
        headers=auth_headers(op_token),
    )
    use_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/filtration/v1/filters/{use_id}/integrity-tests",
        json={"idempotency_key": idem(), "use_id": use_id, "expected_version": 1, "phase": "pre", "result": "fail"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/filtration/v1/filters/{use_id}")).json()
    assert detail["state"] == "FAILED"
    assert detail["requires_deviation"] is True


async def test_stale_version_rejected(client, seeded):
    op_token = await login(client, "sterilization.operator")
    site_id = seeded["site_id"]
    profile_id = str(seeded["sterilization_profile"].id)
    equipment_id = await _create_equipment(client, op_token, site_id, code="EQP-STR-4")
    cycle_id = await _create_cycle(client, op_token, site_id, equipment_id, profile_id)

    resp = await _start(client, op_token, cycle_id, expected_version=99)
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_create_cycle_requires_role(client, seeded):
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    resp = await client.post(
        "/sterilization/v1/cycles",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "process_type": "steam_autoclave",
            "equipment_id": str(seeded["site_id"]), "profile_version_id": str(seeded["sterilization_profile"].id),
            "load_items": [{"item_type": "component", "item_reference": "COMP-1"}],
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_install_filter_unauthenticated_rejected(client, seeded):
    resp = await client.post(
        "/filtration/v1/filters/install",
        json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "filter_serial": "FLT-NOAUTH"},
    )
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# SG-116 follow-up: STR-FR-005/011/022/026.
# ---------------------------------------------------------------------------


async def test_create_cycle_rejects_ineligible_sterilizer(client, seeded):
    op_token = await login(client, "sterilization.operator")
    admin_token = await login(client, "equipment.admin")
    site_id = seeded["site_id"]
    profile_id = str(seeded["sterilization_profile"].id)

    resp = await client.post(
        "/equipment/v1/assets",
        json={"idempotency_key": idem(), "site_id": str(site_id), "equipment_code": "EQP-STR-UNQUAL"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    equipment_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/sterilization/v1/cycles",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "process_type": "steam_autoclave",
            "equipment_id": equipment_id, "profile_version_id": profile_id,
            "load_items": [{"item_type": "component", "item_reference": "COMP-UNQUAL"}],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "STERILIZER_INELIGIBLE"


async def test_indicator_results_captured_on_cycle_data(client, seeded):
    op_token = await login(client, "sterilization.operator")
    site_id = seeded["site_id"]
    profile_id = str(seeded["sterilization_profile"].id)

    equipment_id = await _create_equipment(client, op_token, site_id, code="EQP-STR-IND")
    cycle_id = await _create_cycle(client, op_token, site_id, equipment_id, profile_id)
    await _start(client, op_token, cycle_id, expected_version=1)

    indicator_results = {"bi_lot": "BI-2026-07", "bi_location": "worst_case_1", "bi_result": "no_growth"}
    resp = await client.post(
        f"/sterilization/v1/cycles/{cycle_id}/data",
        json={
            "idempotency_key": idem(), "cycle_id": cycle_id, "expected_version": 2,
            "indicator_results": indicator_results,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/sterilization/v1/cycles/{cycle_id}")).json()
    assert detail["indicator_results"] == indicator_results


async def test_filter_reuse_count_increments_after_accepted_use(client, seeded):
    op_token = await login(client, "sterilization.operator")
    site_id = seeded["site_id"]
    serial = "FLT-REUSE-1"

    async def _install_use_and_complete(expect_reuse_count):
        resp = await client.post(
            "/filtration/v1/filters/install",
            json={"idempotency_key": idem(), "site_id": str(site_id), "filter_serial": serial},
            headers=auth_headers(op_token),
        )
        assert resp.status_code == 200, resp.text
        use_id = resp.json()["aggregate_id"]
        detail = (await client.get(f"/filtration/v1/filters/{use_id}")).json()
        assert detail["reuse_count"] == expect_reuse_count

        resp = await client.post(
            f"/filtration/v1/filters/{use_id}/integrity-tests",
            json={"idempotency_key": idem(), "use_id": use_id, "expected_version": 1, "phase": "pre", "result": "pass"},
            headers=auth_headers(op_token),
        )
        assert resp.status_code == 200, resp.text
        resp = await client.post(
            f"/filtration/v1/filters/{use_id}/integrity-tests",
            json={"idempotency_key": idem(), "use_id": use_id, "expected_version": 2, "phase": "post", "result": "pass"},
            headers=auth_headers(op_token),
        )
        assert resp.status_code == 200, resp.text
        challenge = (
            await client.post(f"/filtration/v1/uses/{use_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(op_token))
        ).json()
        resp = await client.post(
            f"/filtration/v1/uses/{use_id}/complete",
            json={
                "idempotency_key": idem(), "use_id": use_id, "expected_version": 3,
                "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
            },
            headers=auth_headers(op_token),
        )
        assert resp.status_code == 200, resp.text
        detail = (await client.get(f"/filtration/v1/filters/{use_id}")).json()
        assert detail["state"] == "ACCEPTED"

    await _install_use_and_complete(expect_reuse_count=0)
    await _install_use_and_complete(expect_reuse_count=1)


async def test_reprocessing_requires_authorization_reference(client, seeded):
    op_token = await login(client, "sterilization.operator")
    qa_token = await login(client, "qa.reviewer")
    site_id = seeded["site_id"]
    profile_id = str(seeded["sterilization_profile"].id)
    item_reference = "COMP-REPROCESS-1"

    equipment_id = await _create_equipment(client, op_token, site_id, code="EQP-STR-REPRO-1")
    cycle_id = await _create_cycle(client, op_token, site_id, equipment_id, profile_id)
    # (the fixture's load_items use item_reference "COMP-1" -- build this cycle directly to control it)
    resp = await client.post(
        "/sterilization/v1/cycles",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "process_type": "steam_autoclave",
            "equipment_id": equipment_id, "profile_version_id": profile_id,
            "load_items": [{"item_type": "component", "item_reference": item_reference}],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    first_cycle_id = resp.json()["aggregate_id"]
    await _start(client, op_token, first_cycle_id, expected_version=1)
    resp = await _record_data(client, op_token, first_cycle_id, expected_version=2, critical_alarm=True)
    assert resp.status_code == 200, resp.text
    resp = await _review(client, qa_token, first_cycle_id, expected_version=3, decision="reject", reason="Critical alarm")
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/sterilization/v1/cycles/{first_cycle_id}")).json()
    assert detail["state"] == "FAILED"

    equipment_id_2 = await _create_equipment(client, op_token, site_id, code="EQP-STR-REPRO-2")
    resp = await client.post(
        "/sterilization/v1/cycles",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "process_type": "steam_autoclave",
            "equipment_id": equipment_id_2, "profile_version_id": profile_id,
            "load_items": [{"item_type": "component", "item_reference": item_reference}],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "REPROCESSING_AUTHORIZATION_REQUIRED"

    resp = await client.post(
        "/sterilization/v1/cycles",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "process_type": "steam_autoclave",
            "equipment_id": equipment_id_2, "profile_version_id": profile_id,
            "load_items": [{"item_type": "component", "item_reference": item_reference}],
            "reprocessing_authorization_ref": {"deviation_ref": "DEV-2026-042"},
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/sterilization/v1/cycles/{resp.json()['aggregate_id']}")).json()
    assert detail["reprocessing_authorization_ref"] == {"deviation_ref": "DEV-2026-042"}


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded):
    op_token = await login(client, "sterilization.operator")
    site_id = seeded["site_id"]
    key = idem()
    payload = {"idempotency_key": key, "site_id": str(site_id), "filter_serial": "FLT-DUP"}
    first = await client.post("/filtration/v1/filters/install", json=payload, headers=auth_headers(op_token))
    second = await client.post("/filtration/v1/filters/install", json=payload, headers=auth_headers(op_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]
