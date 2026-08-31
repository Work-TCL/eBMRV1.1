"""Document 15 (SPEC-EBMR-006) -- the buildable slice: evaluate a release scope (get-or-create +
eligibility from real signals: QA review currency/completeness, batch hold state, Vault integrity),
release (signature-gated, re-evaluates immediately before commit, creates a Vault release package
snapshot), hold, and reject. New module. Rework/reprocess/destroy and non-batch scope types are out of
scope this pass -- SG-056.
"""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.rel"):
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


async def _released_product_and_recipe(client, admin_token, site_id, tag):
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": f"RELPRD-{tag}", "product_code": f"RELPRD-{tag}",
            "name": "Release Test Product", "version_no": 1, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
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
            "idempotency_key": idem(), "product_business_id": f"RELPRD-{tag}", "recipe_code": f"RELRCP-{tag}", "version_no": 1,
            "product_version_id": product_version_id, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
            "sections": [{"stable_section_code": "SEC-1", "name": "Dispensing", "sequence": 1}],
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


async def _setup(db, client, seeded, tag, *, complete_review=True):
    async with db.begin():
        await _make_admin(db, seeded, f"admin.rel{tag}")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="qa_review_package", action="complete", meaning="Reviewed", signature_required=False))
        db.add(SignaturePolicy(record_type="release_scope", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="release_scope", action="hold", meaning="Approved", signature_required=False))
        db.add(SignaturePolicy(record_type="release_scope", action="reject", meaning="Rejected", signature_required=False))
    admin_token = await login(client, f"admin.rel{tag}")
    product_version_id, recipe_version_id = await _released_product_and_recipe(client, admin_token, seeded["site_id"], tag)

    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": f"BAT-REL-{tag}",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    if complete_review:
        resp = await client.post(
            f"/qa-review/v1/batches/{batch_id}/packages",
            json={"idempotency_key": idem(), "batch_id": batch_id},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200, resp.text
        package_id = resp.json()["aggregate_id"]
        resp = await client.post(
            f"/qa-review/v1/packages/{package_id}/complete",
            json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 1},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200, resp.text

    return admin_token, batch_id


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post(
        "/release/v1/scopes/batch/00000000-0000-0000-0000-000000000000/evaluate", json={"idempotency_key": idem()}, headers={}
    )
    assert resp.status_code == 401


async def test_evaluate_requires_permission(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "1")
    op_token = await login(client, "operator1")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_evaluate_blocked_without_qa_review(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "2", complete_review=False)
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "blocked"
    assert detail["evaluation"]["eligible"] is False
    codes = {b["code"] for b in detail["evaluation"]["blockers"]}
    assert "QA_REVIEW_MISSING" in codes


async def test_evaluate_eligible_and_release(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "3")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "eligible"
    assert detail["evaluation"]["eligible"] is True
    assert detail["evaluation"]["blockers"] == []

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    package = (await client.get(f"/release/v1/scopes/{scope_id}/package", headers=auth_headers(admin_token))).json()
    assert package["scope"]["state"] == "released"
    assert package["scope"]["released_vault_object_id"] is not None
    assert package["decisions"][-1]["decision_code"] == "RELEASED"
    assert package["decisions"][-1]["release_package_hash"] is not None


async def test_release_rejected_when_blocked(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "4", complete_review=False)
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_hold_keeps_eligibility_updating_but_blocks_release(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "5")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/hold",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2, "reason": "quality investigation"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "hold"

    # Re-evaluate: eligibility recomputes (still eligible), but state stays "hold" -- REL-FR-011.
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "hold"
    assert detail["evaluation"]["eligible"] is True

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 4},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_reject(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "6")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/reject",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2, "reason": "customer complaint pattern"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "rejected"


async def test_post_release_hold_preserves_release_decision_history(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "10")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/hold",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 3, "reason": "field complaint under investigation"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    package = (await client.get(f"/release/v1/scopes/{scope_id}/package", headers=auth_headers(admin_token))).json()
    assert package["scope"]["state"] == "hold"
    codes = [d["decision_code"] for d in package["decisions"]]
    assert codes == ["RELEASED", "HOLD"]  # original RELEASED decision retained, never edited/removed


async def test_stale_version_rejected(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "7")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 99},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "8")
    key = idem()
    body = {"idempotency_key": key, "scope_type": "batch", "scope_id": batch_id}
    resp1 = await client.post(f"/release/v1/scopes/batch/{batch_id}/evaluate", json=body, headers=auth_headers(admin_token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post(f"/release/v1/scopes/batch/{batch_id}/evaluate", json=body, headers=auth_headers(admin_token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_release_fails_closed_pending_signature_policy(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.rel9")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="qa_review_package", action="complete", meaning="Reviewed", signature_required=False))
        # Deliberately no SignaturePolicy(record_type="release_scope", action="release", ...) row.
    admin_token = await login(client, "admin.rel9")
    product_version_id, recipe_version_id = await _released_product_and_recipe(client, admin_token, seeded["site_id"], "9")
    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": "BAT-REL-9",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    package_id = resp.json()["aggregate_id"]
    await client.post(
        f"/qa-review/v1/packages/{package_id}/complete",
        json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"
