"""Document 32 (SPEC-QMS-007) -- the buildable slice: create case -> issue SCAR -> supplier response ->
internal review (signed) -> effectiveness -> close (signed), matching the module's own 6-op API list and
the fold-in pattern documented in app/modules/qms/scar_models.py's module docstring. New module.
SCAR-FR-017/018 are out of scope this pass -- see docs/generated/18_SPEC_GAPS.md SG-091.
"""

import uuid

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.qms.scar_models import ScarRecord, SupplierQualityCase
from app.modules.signature.models import SignaturePolicy
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


async def _setup(db, seeded, tag, *, signed=False):
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.scar{tag}")
        # SG-138 (2026-09-10): Document 106 section 9 rows 95/96 -- review `Reviewed` by a "QA Reviewer"
        # independent of the performer; close `Approved` by a "QA Releaser" independent of the owner.
        for action, meaning, role in (("review", "Reviewed", "QA Reviewer"), ("close", "Approved", "QA Releaser")):
            db.add(SignaturePolicy(
                record_type="scar_record", action=action, meaning=meaning, signature_required=signed,
                required_role_id=(seeded["roles"][role].id if signed else None),
                requires_independent_signer=signed,
            ))
    return owner


async def _indep_user(db, seeded, username, role_name):
    """A signer holding `role_name` who is not the SCAR's internal owner (Document 106 section 9)."""
    async with db.begin():
        user = User(
            username=username, email=f"{username}@example.com", full_name=role_name,
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


async def _create_supplier(client, token, code):
    resp = await client.post(
        "/suppliers/v1",
        json={
            "idempotency_key": idem(), "supplier_code": code, "legal_name": f"{code} Supply Co.",
            "role_type": "supplier", "country": "US",
            "sites": [{"site_name": "Main Site", "country": "US", "manufacturer_flag": False}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


def _case_body(site_id, supplier_id, owner_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "case_number": f"SQC-{uuid.uuid4().hex[:8]}",
        "supplier_id": supplier_id, "affected_lots": [{"lot_id": str(uuid.uuid4())}],
        "defect_code": "DEF-SCAR-001", "severity": "major", "internal_owner_subject_id": str(owner_id),
    }
    body.update(overrides)
    return body


async def _create_case(client, token, site_id, supplier_id, owner_id, **overrides):
    resp = await client.post("/qms/v1/supplier-cases", json=_case_body(site_id, supplier_id, owner_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _issue_scar(client, token, case_id, case_expected_version=1, **overrides):
    body = {
        "idempotency_key": idem(), "case_id": case_id, "case_expected_version": case_expected_version,
        "scar_number": f"SCAR-{uuid.uuid4().hex[:8]}", "problem_statement": "Incoming lot failed identity test.",
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/supplier-cases/{case_id}/scar", json=body, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _respond(client, token, scar_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "scar_id": scar_id, "expected_version": expected_version,
        "acknowledgment": {"contact": "quality@supplier.example", "acknowledged_at": "2026-08-21T00:00:00Z"},
        "supplier_root_cause": {"statement": "Calibration drift on incoming inspection gauge."},
        "supplier_actions": {"corrective_action": "Recalibrate gauge and retrain operators.", "evidence": "cal-cert-9931"},
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/scars/{scar_id}/response", json=body, headers=auth_headers(token))
    return resp


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/supplier-cases", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_case_requires_affected_lots(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.scar1")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-1")
    resp = await client.post(
        "/qms/v1/supplier-cases", json=_case_body(seeded["site_id"], supplier_id, owner.id, affected_lots=[]), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "SCAR_SOURCE_REQUIRED"


async def test_full_lifecycle_success(client, seeded, db):
    owner = await _setup(db, seeded, "2", signed=False)
    token = await login(client, "admin.scar2")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-2")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)

    scar_id = await _issue_scar(client, token, case_id)

    resp = await _respond(client, token, scar_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/review",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 2, "decision": "accepted", "rationale": "Root cause and CAPA are adequate."},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # 2 -> 3

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/effectiveness",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 3, "result": "pass", "evidence": {"incoming_lots_checked": 5}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # 3 -> 4

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/close",
        json={
            "idempotency_key": idem(), "scar_id": scar_id, "expected_version": 4,
            "source_status_decision": "no_change", "conclusion": "Effectiveness confirmed; no source action required.",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resulting_version"] == 5


async def test_review_rejected_bounces_back_and_blocks_effectiveness(client, seeded, db):
    owner = await _setup(db, seeded, "3", signed=False)
    token = await login(client, "admin.scar3")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-3")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)
    await _respond(client, token, scar_id, 1)

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/review",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 2, "decision": "rejected", "rationale": "Root cause is superficial."},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # 2 -> 3, state bounces back to SUPPLIER_RESPONSE

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/effectiveness",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 3, "result": "pass"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SCAR_REVIEW_REJECTED"


async def test_review_requires_complete_response(client, seeded, db):
    owner = await _setup(db, seeded, "4", signed=False)
    token = await login(client, "admin.scar4")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-4")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)
    await _respond(client, token, scar_id, 1, supplier_actions=None)

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/review",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 2, "decision": "accepted", "rationale": "ok"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "SUPPLIER_RESPONSE_INCOMPLETE"


async def test_close_requires_effectiveness_pass(client, seeded, db):
    owner = await _setup(db, seeded, "5", signed=False)
    token = await login(client, "admin.scar5")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-5")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)
    await _respond(client, token, scar_id, 1)
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/review",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 2, "decision": "accepted", "rationale": "ok"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/effectiveness",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 3, "result": "fail"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/close",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 4, "source_status_decision": "no_change", "conclusion": "done"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "EFFECTIVENESS_REQUIRED"


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "6", signed=False)
    token = await login(client, "admin.scar6")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-6")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)

    resp = await _respond(client, token, scar_id, 99)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_idempotent_replay_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "7", signed=False)
    token = await login(client, "admin.scar7")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-7")
    key = idem()
    body = _case_body(seeded["site_id"], supplier_id, owner.id)
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/supplier-cases", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/supplier-cases", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]

    body2 = dict(body)
    body2["severity"] = "critical"
    resp3 = await client.post("/qms/v1/supplier-cases", json=body2, headers=auth_headers(token))
    assert resp3.status_code == 409, resp3.text
    assert resp3.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_close_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "8", signed=True)
    await _indep_user(db, seeded, "qa.scar8", "QA Reviewer")
    token = await login(client, "admin.scar8")
    reviewer_token = await login(client, "qa.scar8")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-8")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)
    await _respond(client, token, scar_id, 1)
    # Independent QA Reviewer, correct role, no challenge -> still MISSING_SIGNATURE.
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/review",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 2, "decision": "accepted", "rationale": "ok"},
        headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_source_suspended_blocks_new_case(client, seeded, db):
    owner = await _setup(db, seeded, "9", signed=False)
    token = await login(client, "admin.scar9")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-9")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)
    await _respond(client, token, scar_id, 1)
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/review",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 2, "decision": "accepted", "rationale": "ok"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/effectiveness",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 3, "result": "pass"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/close",
        json={
            "idempotency_key": idem(), "scar_id": scar_id, "expected_version": 4,
            "source_status_decision": "suspend", "conclusion": "Recurrent failure -- source suspended pending resolution.",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/qms/v1/supplier-cases", json=_case_body(seeded["site_id"], supplier_id, owner.id), headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SUPPLIER_SOURCE_SUSPENDED"


async def test_repeat_issue_detected_across_cases(client, seeded, db):
    owner = await _setup(db, seeded, "10", signed=False)
    token = await login(client, "admin.scar10")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-10")

    first_case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id, defect_code="DEF-REPEAT-01")
    first_scar_id = await _issue_scar(client, token, first_case_id)

    second_case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id, defect_code="DEF-REPEAT-01")
    resp = await client.post(
        f"/qms/v1/supplier-cases/{second_case_id}/scar",
        json={
            "idempotency_key": idem(), "case_id": second_case_id, "case_expected_version": 1,
            "scar_number": f"SCAR-{uuid.uuid4().hex[:8]}", "problem_statement": "Same defect recurring.",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    second_scar_id = resp.json()["aggregate_id"]

    first_scar = await db.get(ScarRecord, uuid.UUID(first_scar_id))
    second_scar = await db.get(ScarRecord, uuid.UUID(second_scar_id))
    assert first_scar.is_repeat_issue is False
    assert second_scar.is_repeat_issue is True
    assert second_scar.related_case_ids == [first_case_id]


async def test_containment_at_case_creation(client, seeded, db):
    owner = await _setup(db, seeded, "11", signed=False)
    token = await login(client, "admin.scar11")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-11")
    case_id = await _create_case(
        client, token, seeded["site_id"], supplier_id, owner.id,
        containment={"holds": [{"target_type": "lot", "target_id": str(uuid.uuid4())}]},
    )
    case = await db.get(SupplierQualityCase, uuid.UUID(case_id))
    assert case.state == "CONTAINMENT"
    assert case.containment is not None


async def test_closure_captures_requalification_capa_and_alternate_source(client, seeded, db):
    owner = await _setup(db, seeded, "12", signed=False)
    token = await login(client, "admin.scar12")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-12")
    case_id = await _create_case(
        client, token, seeded["site_id"], supplier_id, owner.id,
        alternate_source_ref={"change_control_ref": "CC-9001", "rationale": "Emergency alternate source pending resolution."},
    )
    case = await db.get(SupplierQualityCase, uuid.UUID(case_id))
    assert case.alternate_source_ref is not None

    scar_id = await _issue_scar(client, token, case_id)
    await _respond(client, token, scar_id, 1)
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/review",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 2, "decision": "accepted", "rationale": "ok"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/effectiveness",
        json={"idempotency_key": idem(), "scar_id": scar_id, "expected_version": 3, "result": "pass"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/close",
        json={
            "idempotency_key": idem(), "scar_id": scar_id, "expected_version": 4,
            "source_status_decision": "requalify", "conclusion": "Requalification and internal CAPA required.",
            "requalification_required": True, "requalification_rationale": "Recurring defect pattern.",
            "capa_required": True, "capa_rationale": "Systemic gauge calibration issue.",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    scar = await db.get(ScarRecord, uuid.UUID(scar_id))
    assert scar.requalification_required is True
    assert scar.capa_required is True
    assert scar.source_status_decision == "requalify"


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.scar20")
    token = await login(client, "admin.scar20")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-20")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)
    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/signature-challenges", json={"action": "review"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_scar(client, seeded, db):
    owner = await _setup(db, seeded, "21")
    token = await login(client, "admin.scar21")
    resp = await client.post(
        f"/qms/v1/scars/{uuid.uuid4()}/signature-challenges", json={"action": "review"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_review(client, seeded, db):
    owner = await _setup(db, seeded, "22", signed=True)
    await _indep_user(db, seeded, "qa.scar22", "QA Reviewer")
    token = await login(client, "admin.scar22")
    reviewer_token = await login(client, "qa.scar22")
    supplier_id = await _create_supplier(client, token, "SUP-SCAR-22")
    case_id = await _create_case(client, token, seeded["site_id"], supplier_id, owner.id)
    scar_id = await _issue_scar(client, token, case_id)
    resp = await _respond(client, token, scar_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/signature-challenges", json={"action": "review"}, headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Reviewed"  # Document 106 section 9 row 96

    resp = await client.post(
        f"/qms/v1/scars/{scar_id}/review",
        json={
            "idempotency_key": idem(), "scar_id": scar_id, "expected_version": 2, "decision": "accepted",
            "rationale": "Root cause and CAPA are adequate.",
            "challenge_id": body["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
