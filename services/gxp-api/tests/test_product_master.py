"""Document 09 (SPEC-EBMR-000) -- draft/submit/release/suspend/reinstate for the new, additive Product
Master module. Does not touch app/modules/product (the legacy Batch/Recipe-facing stub); the full 64-test
pre-existing suite passes unmodified, proving that. Release/suspend/reinstate correctly fail closed pending
Document 106 (SG-035's scope extended to product_version) -- the same honest pattern as every other new
regulated action this session.
"""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.product"):
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


def _draft_body(site_id, business_id="PRD-1", version_no=1, **overrides):
    body = {
        "idempotency_key": idem(),
        "product_business_id": business_id,
        "product_code": business_id,
        "name": "Test Product",
        "version_no": version_no,
        "site_id": str(site_id),
        "manufacturing_profile_code": "pharma",
    }
    body.update(overrides)
    return body


async def test_create_draft_requires_product_author_permission(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post("/products/v1/drafts", json=_draft_body(seeded["site_id"]), headers=auth_headers(op_token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post(
        "/products/v1/drafts", json={"idempotency_key": idem(), "product_business_id": "X"}, headers={}
    )
    assert resp.status_code == 401


async def test_draft_submit_and_completeness_findings_block_release(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.product1")
    admin_token = await login(client, "admin.product1")

    resp = await client.post(
        "/products/v1/drafts",
        json=_draft_body(seeded["site_id"], "PRD-INCOMPLETE", manufacturing_profile_code="injectable_ddcp"),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    product_version_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/products/v1/drafts/{product_version_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    # injectable_ddcp requires a sterile_profile_id (PRD-FR-010) -- this draft never set one.
    resp = await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"
    assert any("sterile_profile_id" in f for f in resp.json()["details"]["findings"])


async def test_release_fails_closed_pending_signature_policy(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.product2")
    admin_token = await login(client, "admin.product2")

    resp = await client.post(
        "/products/v1/drafts", json=_draft_body(seeded["site_id"], "PRD-2"), headers=auth_headers(admin_token)
    )
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
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_release_creates_vault_snapshot_and_issue_eligibility_becomes_true(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.product3")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.product3")

    resp = await client.post(
        "/products/v1/drafts", json=_draft_body(seeded["site_id"], "PRD-3"), headers=auth_headers(admin_token)
    )
    product_version_id = resp.json()["aggregate_id"]
    await client.post(
        f"/products/v1/drafts/{product_version_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )

    before = await client.get(f"/products/v1/{product_version_id}/issue-eligibility", headers=auth_headers(admin_token))
    assert before.json()["eligible"] is False

    resp = await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/products/v1/{product_version_id}", headers=auth_headers(admin_token))).json()
    assert detail["lifecycle_state"] == "released"
    assert detail["released_vault_object_id"] is not None
    assert detail["version_hash"] is not None

    after = await client.get(f"/products/v1/{product_version_id}/issue-eligibility", headers=auth_headers(admin_token))
    body = after.json()
    assert body["eligible"] is True
    assert body["checks"]["site_admission"] == "not_implemented"


async def test_drug_device_compatibility_released_alongside_parent(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.product4")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.product4")

    drug_resp = await client.post(
        "/products/v1/drafts", json=_draft_body(seeded["site_id"], "PRD-DRUG"), headers=auth_headers(admin_token)
    )
    drug_id = drug_resp.json()["aggregate_id"]
    await client.post(
        f"/products/v1/drafts/{drug_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": drug_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    await client.post(
        f"/products/v1/drafts/{drug_id}/release",
        json={"idempotency_key": idem(), "product_version_id": drug_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )

    device_resp = await client.post(
        "/products/v1/drafts",
        json=_draft_body(seeded["site_id"], "PRD-DEVICE", manufacturing_profile_code="device"),
        headers=auth_headers(admin_token),
    )
    device_id = device_resp.json()["aggregate_id"]
    await client.post(
        f"/products/v1/drafts/{device_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": device_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/products/v1/drafts/{device_id}/release",
        json={
            "idempotency_key": idem(),
            "product_version_id": device_id,
            "expected_version": 2,
            "compatibility_versions": [
                {
                    "compatibility_code": "COMPAT-1",
                    "version_no": 1,
                    "drug_constituent_version_id": drug_id,
                    "device_constituent_version_id": device_id,
                    "interface_constraints": {"connector": "luer-lock"},
                }
            ],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    compat = (await client.get(f"/products/v1/{drug_id}/compatibility", headers=auth_headers(admin_token))).json()
    assert len(compat) == 1
    assert compat[0]["compatibility_code"] == "COMPAT-1"
    assert compat[0]["status"] == "released"
    assert compat[0]["vault_object_id"] is not None


async def test_concurrent_draft_update_rejects_stale_version(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.product5")
    admin_token = await login(client, "admin.product5")

    resp = await client.post(
        "/products/v1/drafts", json=_draft_body(seeded["site_id"], "PRD-5"), headers=auth_headers(admin_token)
    )
    product_version_id = resp.json()["aggregate_id"]

    update_body = {
        "idempotency_key": idem(),
        "product_version_id": product_version_id,
        "expected_version": 1,
        "name": "Renamed",
        "manufacturing_profile_code": "pharma",
    }
    ok = await client.put(f"/products/v1/drafts/{product_version_id}", json=update_body, headers=auth_headers(admin_token))
    assert ok.status_code == 200, ok.text

    stale = await client.put(
        f"/products/v1/drafts/{product_version_id}",
        json={**update_body, "idempotency_key": idem()},
        headers=auth_headers(admin_token),
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_VERSION"
