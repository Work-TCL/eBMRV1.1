"""MUT-FR-014/RUL-FR-016 — the optional release-gating hook wired into disposition_material_lot (and
release_batch, same helper) via app/modules/rules/commands.py::evaluate_release_gate. Every other test in
this suite proves the no-op path implicitly (none of them define a rule at the conventional rule_id, so
releases/dispositions proceed exactly as before this pass). This file proves the gate actually blocks once
a deployment authors and releases a matching rule.
"""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_material_flow import _create_material, _receive_lot


async def _make_admin(db, seeded, username="admin.gate"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name="Test Admin",
        password_hash=hash_password(DEMO_PASSWORD),
        status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


async def _author_and_release_rule(client, admin_token, db, *, rule_id, expression_ast):
    async with db.begin():
        db.add(SignaturePolicy(record_type="rule", action="release", meaning="Released", signature_required=False))

    resp = await client.post(
        "/rules/v1/drafts",
        json={
            "idempotency_key": idem(),
            "rule_id": rule_id,
            "rule_type": "eligibility",
            "semantic_version": "1.0.0",
            "expression_ast": expression_ast,
            "input_contract": {"available_quantity": {"type": "decimal"}, "received_quantity": {"type": "decimal"}},
            "output_contract": {"eligible": {"type": "boolean"}},
            "unit_policy": {},
            "precision_policy": {"calculation_class": "CC-3"},
            "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rule_object_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/validate",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/release",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return rule_object_id


async def test_disposition_blocked_by_a_released_eligibility_rule_that_fails(client, seeded, db):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]

    async with db.begin():
        await _make_admin(db, seeded, "admin.gate1")
    admin_token = await login(client, "admin.gate1")

    material_id = await _create_material(client, op_token, site_id, code="RM-GATE1")
    lot_id = await _receive_lot(client, op_token, material_id, site_id, internal_lot="LOT-GATE1", quantity="100.000000")

    # available_quantity (100) will never satisfy >= 1000 -- this rule always fails for this lot.
    await _author_and_release_rule(
        client,
        admin_token,
        db,
        rule_id=f"material-lot-release-eligibility:{material_id}",
        expression_ast={"op": "gte", "args": [{"var": "available_quantity"}, "1000"]},
    )

    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "disposition"},
            headers=auth_headers(qc_token),
        )
    ).json()
    resp = await client.post(
        f"/material-lots/{lot_id}/disposition",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "decision": "released",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qc_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "RULE_GATE_FAILED"

    detail = (await client.get(f"/material-lots/{lot_id}")).json()
    assert detail["status"] == "quarantine"  # blocked -- never transitioned


async def test_disposition_allowed_by_a_released_eligibility_rule_that_passes(client, seeded, db):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]

    async with db.begin():
        await _make_admin(db, seeded, "admin.gate2")
    admin_token = await login(client, "admin.gate2")

    material_id = await _create_material(client, op_token, site_id, code="RM-GATE2")
    lot_id = await _receive_lot(client, op_token, material_id, site_id, internal_lot="LOT-GATE2", quantity="100.000000")

    # available_quantity (100) satisfies >= 1 -- this rule always passes for this lot.
    await _author_and_release_rule(
        client,
        admin_token,
        db,
        rule_id=f"material-lot-release-eligibility:{material_id}",
        expression_ast={"op": "gte", "args": [{"var": "available_quantity"}, "1"]},
    )

    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "disposition"},
            headers=auth_headers(qc_token),
        )
    ).json()
    resp = await client.post(
        f"/material-lots/{lot_id}/disposition",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "decision": "released",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qc_token),
    )
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/material-lots/{lot_id}")).json()
    assert detail["status"] == "released"
