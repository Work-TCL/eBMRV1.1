"""Document 14 (SPEC-EBMR-005) -- the buildable slice: create a QA review package against a batch (with
inline completeness computed from real batch-hold-state + Vault-integrity + audit-correction signals),
reindex it, and complete it (signature-gated, gated on computed completeness). New module. Everything
needing qa_review_item/qa_review_comment or the modules SG-054 lists (QC/materials/equipment/environment/
genealogy-completeness/packaging/yield review, itemised disposition, reviewer comments, checklists,
multi-reviewer) is out of scope this pass -- SG-053/SG-054.
"""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.qa"):
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
            "idempotency_key": idem(), "product_business_id": f"QAPRD-{tag}", "product_code": f"QAPRD-{tag}",
            "name": "QA Test Product", "version_no": 1, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
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
            "idempotency_key": idem(), "product_business_id": f"QAPRD-{tag}", "recipe_code": f"QARCP-{tag}", "version_no": 1,
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


async def _setup(db, client, seeded, tag, *, issue=True):
    async with db.begin():
        await _make_admin(db, seeded, f"admin.qa{tag}")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="qa_review_package", action="complete", meaning="Reviewed", signature_required=False))
    admin_token = await login(client, f"admin.qa{tag}")
    product_version_id, recipe_version_id = await _released_product_and_recipe(client, admin_token, seeded["site_id"], tag)

    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": f"BAT-QA-{tag}",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["aggregate_id"]
    if issue:
        resp = await client.post(
            f"/batches/v1/{batch_id}/issue",
            json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200, resp.text
    return admin_token, batch_id


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qa-review/v1/batches/00000000-0000-0000-0000-000000000000/packages", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_package_requires_permission(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "1")
    op_token = await login(client, "operator1")
    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_create_package_complete_when_clean(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "2")
    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    package_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/qa-review/v1/packages/{package_id}", headers=auth_headers(admin_token))).json()
    assert detail["completeness_status"] == "complete"
    assert detail["state"] == "READY_FOR_REVIEW"
    assert detail["stale"] is False

    exceptions = (await client.get(f"/qa-review/v1/packages/{package_id}/exceptions", headers=auth_headers(admin_token))).json()
    assert exceptions["corrections"] == []
    assert exceptions["integrity_check"]["digest_valid"] is True


async def test_duplicate_package_for_same_batch_rejected(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "3")
    body = {"idempotency_key": idem(), "batch_id": batch_id}
    resp = await client.post(f"/qa-review/v1/batches/{batch_id}/packages", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    body2 = {"idempotency_key": idem(), "batch_id": batch_id}
    resp = await client.post(f"/qa-review/v1/batches/{batch_id}/packages", json=body2, headers=auth_headers(admin_token))
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_hold_makes_package_blocked_and_completion_rejected(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "4")
    await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    await client.post(
        f"/batches/v1/{batch_id}/hold",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 3},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    package_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/qa-review/v1/packages/{package_id}", headers=auth_headers(admin_token))).json()
    assert detail["completeness_status"] == "blocked"

    resp = await client.post(
        f"/qa-review/v1/packages/{package_id}/complete",
        json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_complete_package_and_reopen_on_batch_change(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "5")
    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    package_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/qa-review/v1/packages/{package_id}/complete",
        json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/qa-review/v1/packages/{package_id}", headers=auth_headers(admin_token))).json()
    assert detail["state"] == "REVIEW_COMPLETE"
    assert detail["completed_at"] is not None

    # Batch changes underneath the completed review (start -> version bump) -- reindex should reopen it.
    await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    detail = (await client.get(f"/qa-review/v1/packages/{package_id}", headers=auth_headers(admin_token))).json()
    assert detail["stale"] is True

    resp = await client.post(
        f"/qa-review/v1/packages/{package_id}/reindex",
        json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/qa-review/v1/packages/{package_id}", headers=auth_headers(admin_token))).json()
    assert detail["state"] == "REOPENED"


async def test_stale_version_rejected(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "6")
    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    package_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/qa-review/v1/packages/{package_id}/complete",
        json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 99},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "7")
    key = idem()
    body = {"idempotency_key": key, "batch_id": batch_id}
    resp1 = await client.post(f"/qa-review/v1/batches/{batch_id}/packages", json=body, headers=auth_headers(admin_token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post(f"/qa-review/v1/batches/{batch_id}/packages", json=body, headers=auth_headers(admin_token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_complete_fails_closed_pending_signature_policy(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.qa9")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
        # Deliberately no SignaturePolicy(record_type="qa_review_package", action="complete", ...) row.
    admin_token = await login(client, "admin.qa9")
    product_version_id, recipe_version_id = await _released_product_and_recipe(client, admin_token, seeded["site_id"], "9")
    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": "BAT-QA-9",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    package_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/qa-review/v1/packages/{package_id}/complete",
        json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_dashboard_lists_packages(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "8")
    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    package_id = resp.json()["aggregate_id"]

    resp = await client.get(f"/qa-review/v1/dashboard?site_id={seeded['site_id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    assert any(p["package_id"] == package_id for p in resp.json()["packages"])

    resp = await client.get(f"/qa-review/v1/dashboard?site_id={seeded['site_id']}&state=REVIEW_COMPLETE", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    assert all(p["package_id"] != package_id for p in resp.json()["packages"])
