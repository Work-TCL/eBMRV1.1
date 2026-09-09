"""Document 09 (SPEC-EBMR-000) -- draft/submit/release/suspend/reinstate for the new, additive Product
Master module. Does not touch app/modules/product (the legacy Batch/Recipe-facing stub); the full 64-test
pre-existing suite passes unmodified, proving that. Release now resolves to a real signature policy
(SG-035 PARTIALLY RESOLVED 2026-09-07, self-signed by Admin); suspend/reinstate still correctly fail
closed pending Document 106 (SG-035's remaining scope).
"""

import uuid

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


async def _make_user_with_role(db, seeded, username, role_name):
    user = User(
        username=username, email=f"{username}@example.com", full_name=username,
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


def _add_release_signature_policy(db, seeded):
    """SG-035 PARTIALLY RESOLVED 2026-09-07 (project-owner-directed: self-signed by Admin) -- the real
    values `scripts/seed.py`'s SIGNATURE_POLICY_FLOOR now carries for the live DB. Added per-test, not
    globally in conftest.py's own SignaturePolicy list, because at least 6 other test files
    (test_release.py etc.) already add their own local product_version/release row (signature_required=False,
    for cheap unsigned-release test setup) and a global row here would collide with every one of them on
    UniqueConstraint(record_type, action)."""
    db.add(
        SignaturePolicy(
            record_type="product_version", action="release", meaning="Released",
            required_role_id=seeded["roles"]["Admin"].id, requires_independent_signer=False,
            signature_required=True, reason_required=False, policy_source="PLATFORM_FLOOR",
        )
    )


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


async def test_create_draft_rejects_duplicate_product_code_under_a_different_business_id(client, seeded, db):
    """ProductVersion carries two independent UniqueConstraints -- (product_business_id, version_no) and
    (product_code, version_no) (migration d5d48a66187f). Only the first was pre-checked in application
    code; a second draft reusing the same product_code (under a different business_id) at the same
    version_no used to fall through to the raw DB constraint uncaught, surfacing as an opaque
    SYSTEM_FAULT instead of a clear validation error."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.product.codedup")
    admin_token = await login(client, "admin.product.codedup")

    first = await client.post(
        "/products/v1/drafts",
        json=_draft_body(seeded["site_id"], "PRD-CODEDUP-A", product_code="SHARED-CODE-001"),
        headers=auth_headers(admin_token),
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        "/products/v1/drafts",
        json=_draft_body(seeded["site_id"], "PRD-CODEDUP-B", product_code="SHARED-CODE-001"),
        headers=auth_headers(admin_token),
    )
    assert second.status_code == 422, second.text
    assert second.json()["code"] == "VALIDATION_FAILED"
    assert "product_code" in second.json()["message"]


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


async def test_release_requires_signature_and_succeeds_with_a_valid_challenge(client, seeded, db):
    """SG-035 PARTIALLY RESOLVED 2026-09-07 (project-owner-directed, self-signed by Admin): release now
    resolves to a real Document 106 floor row and goes through the same challenge/reauth-password
    ceremony every other signed action in this codebase uses."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.product2")
        _add_release_signature_policy(db, seeded)
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

    # Releasing without a challenge/password is rejected -- the signature is actually enforced, not just
    # nominally resolved.
    unsigned = await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert unsigned.status_code == 428, unsigned.text
    assert unsigned.json()["code"] == "MISSING_SIGNATURE"

    challenge = (
        await client.post(
            f"/products/v1/{product_version_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(admin_token),
        )
    ).json()
    assert challenge["meaning"] == "Released"

    resp = await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={
            "idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/products/v1/{product_version_id}", headers=auth_headers(admin_token))).json()
    assert detail["lifecycle_state"] == "released"

    # suspend/reinstate remain unresolved -- SG-035's remaining scope, deliberately not extended here.
    suspend_resp = await client.post(
        f"/products/v1/{product_version_id}/suspend",
        json={
            "idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 3,
            "reason": "test",
        },
        headers=auth_headers(admin_token),
    )
    assert suspend_resp.status_code == 409
    assert suspend_resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_product_authored_by_process_engineer_is_released_by_an_independent_qa_releaser(client, seeded, db):
    """Decision 2 (2026-09-08): Process Engineer holds product.author (not product.release); QA Releaser
    holds product.release; the product_version/release signature policy adds person-level independence
    (author != releaser -> SOD_CONFLICT), mirroring recipe_version/release."""
    async with db.begin():
        dual = await _make_user_with_role(db, seeded, "dual.product", "Process Engineer")
        db.add(UserSiteRole(user_id=dual.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        await _make_user_with_role(db, seeded, "pe.product", "Process Engineer")
        await _make_user_with_role(db, seeded, "releaser.product", "QA Releaser")
        db.add(
            SignaturePolicy(
                record_type="product_version", action="release", meaning="Released",
                required_role_id=seeded["roles"]["QA Releaser"].id, requires_independent_signer=True,
                signature_required=True, policy_source="PLATFORM_FLOOR",
            )
        )
    pe_token = await login(client, "pe.product")
    dual_token = await login(client, "dual.product")
    releaser_token = await login(client, "releaser.product")

    pv = (
        await client.post("/products/v1/drafts", json=_draft_body(seeded["site_id"], "PRD-PE"), headers=auth_headers(pe_token))
    ).json()["aggregate_id"]
    await client.post(
        f"/products/v1/drafts/{pv}/submit",
        json={"idempotency_key": idem(), "product_version_id": pv, "expected_version": 1},
        headers=auth_headers(pe_token),
    )
    body = {"idempotency_key": idem(), "product_version_id": pv, "expected_version": 2}

    # Process Engineer cannot release (no product.release permission -> router gate).
    resp = await client.post(f"/products/v1/drafts/{pv}/release", json=body, headers=auth_headers(pe_token))
    assert resp.status_code == 403 and resp.json()["code"] == "ROLE_MISSING"

    # The dual-role user releasing a product THEY authored -> independence blocks it.
    pv2 = (
        await client.post("/products/v1/drafts", json=_draft_body(seeded["site_id"], "PRD-DUAL"), headers=auth_headers(dual_token))
    ).json()["aggregate_id"]
    await client.post(
        f"/products/v1/drafts/{pv2}/submit",
        json={"idempotency_key": idem(), "product_version_id": pv2, "expected_version": 1},
        headers=auth_headers(dual_token),
    )
    resp = await client.post(
        f"/products/v1/drafts/{pv2}/release",
        json={"idempotency_key": idem(), "product_version_id": pv2, "expected_version": 2},
        headers=auth_headers(dual_token),
    )
    assert resp.status_code == 409 and resp.json()["code"] == "SOD_CONFLICT"

    # Independent QA Releaser: unsigned -> 428, signed -> released.
    resp = await client.post(
        f"/products/v1/drafts/{pv}/release", json={**body, "idempotency_key": idem()}, headers=auth_headers(releaser_token)
    )
    assert resp.status_code == 428
    ch = (
        await client.post(
            f"/products/v1/{pv}/signature-challenges", json={"action": "release"}, headers=auth_headers(releaser_token)
        )
    ).json()
    resp = await client.post(
        f"/products/v1/drafts/{pv}/release",
        json={**body, "idempotency_key": idem(), "challenge_id": ch["challenge_id"], "reauth_password": DEMO_PASSWORD},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    assert (await client.get(f"/products/v1/{pv}", headers=auth_headers(releaser_token))).json()["lifecycle_state"] == "released"


async def test_create_draft_rejects_sterile_profile_id_with_no_real_registry_match(client, seeded, db):
    """PRD-FR-010: a `sterile_profile_id` that doesn't reference a real row in
    `equipment.aseptic_profile_versions` must be rejected at draft create/update, not silently accepted
    the way a raw UUID text field used to."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.product.sterile1")
    admin_token = await login(client, "admin.product.sterile1")

    resp = await client.post(
        "/products/v1/drafts",
        json=_draft_body(
            seeded["site_id"],
            "PRD-STERILE-FAKE",
            manufacturing_profile_code="injectable_ddcp",
            sterile_profile_id=str(uuid.uuid4()),
        ),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"
    assert "sterile_profile_id" in resp.json()["message"]


async def test_create_and_update_draft_accept_a_real_released_sterile_profile(client, seeded, db):
    """The seeded `equipment.aseptic_profile_versions` row (ASP-PROC-001, RELEASED) is a real registry
    entry -- referencing it must be accepted at both create and update."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.product.sterile2")
    admin_token = await login(client, "admin.product.sterile2")
    real_profile_id = str(seeded["aseptic_profile"].id)

    resp = await client.post(
        "/products/v1/drafts",
        json=_draft_body(
            seeded["site_id"],
            "PRD-STERILE-REAL",
            manufacturing_profile_code="injectable_ddcp",
            sterile_profile_id=real_profile_id,
        ),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    product_version_id = resp.json()["aggregate_id"]

    resp = await client.get(f"/products/v1/{product_version_id}", headers=auth_headers(admin_token))
    assert resp.json()["sterile_profile_id"] == real_profile_id

    # A bad value on update is rejected too -- the FK check isn't only a create-time convenience.
    resp = await client.put(
        f"/products/v1/drafts/{product_version_id}",
        json={
            "idempotency_key": idem(),
            "product_version_id": product_version_id,
            "expected_version": 1,
            "name": "Test Product",
            "manufacturing_profile_code": "injectable_ddcp",
            "sterile_profile_id": str(uuid.uuid4()),
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_sterile_profiles_endpoint_lists_real_registry_for_the_site(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.product.sterile3")
    admin_token = await login(client, "admin.product.sterile3")

    resp = await client.get(
        f"/products/v1/sterile-profiles?site_id={seeded['site_id']}", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200, resp.text
    profiles = resp.json()
    assert any(p["id"] == str(seeded["aseptic_profile"].id) and p["profile_number"] == "ASP-PROC-001" for p in profiles)
    assert all(p["state"] == "RELEASED" for p in profiles)


async def test_release_creates_vault_snapshot_and_issue_eligibility_becomes_true(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.product3")
        _add_release_signature_policy(db, seeded)
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

    challenge = (
        await client.post(
            f"/products/v1/{product_version_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(admin_token),
        )
    ).json()

    resp = await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={
            "idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
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


async def _release_with_signature(client, admin_token, product_version_id, expected_version, **extra_body):
    challenge = (
        await client.post(
            f"/products/v1/{product_version_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(admin_token),
        )
    ).json()
    return await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={
            "idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": expected_version,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
            **extra_body,
        },
        headers=auth_headers(admin_token),
    )


async def test_drug_device_compatibility_released_alongside_parent(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.product4")
        _add_release_signature_policy(db, seeded)
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
    await _release_with_signature(client, admin_token, drug_id, 2)

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
    resp = await _release_with_signature(
        client, admin_token, device_id, 2,
        compatibility_versions=[
            {
                "compatibility_code": "COMPAT-1",
                "version_no": 1,
                "drug_constituent_version_id": drug_id,
                "device_constituent_version_id": device_id,
                "interface_constraints": {"connector": "luer-lock"},
            }
        ],
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
