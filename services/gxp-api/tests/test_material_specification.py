"""SG-057 (architecture rule C-014) -- draft/release for the new, additive MaterialSpecificationVersion
module. Release now resolves to a real signature policy (SG-185 RESOLVED 2026-09-18,
project-owner-directed: same shape as product_version/release -- "Released" by an independent QA
Releaser).
"""

import uuid

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.material.models import Material
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_user_with_role(db, seeded, username, role_name):
    user = User(
        username=username, email=f"{username}@example.com", full_name=username,
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


async def _make_material(db, seeded, code="MAT-SPEC-TEST-001"):
    material = Material(site_id=seeded["site_id"], code=code, name="Test Material", uom="kg")
    db.add(material)
    await db.flush()
    return material


def _draft_body(site_id, material_id, business_id="MATSPEC-1", version_no=1, **overrides):
    body = {
        "idempotency_key": idem(),
        "material_spec_business_id": business_id,
        "version_no": version_no,
        "material_id": str(material_id),
        "name": "Test Material Specification",
        "site_id": str(site_id),
    }
    body.update(overrides)
    return body


async def test_create_draft_requires_material_spec_author_permission(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded)
        await _make_user_with_role(db, seeded, "qa.reviewer.matspec", "QA Reviewer")
    token = await login(client, "qa.reviewer.matspec")
    resp = await client.post(
        "/material-specifications/v1/drafts", json=_draft_body(seeded["site_id"], material.id), headers=auth_headers(token)
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post(
        "/material-specifications/v1/drafts",
        json={"idempotency_key": idem(), "material_spec_business_id": "X"},
        headers={},
    )
    assert resp.status_code == 401


async def test_create_draft_succeeds_for_process_engineer_and_is_readable(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-TEST-002")
        await _make_user_with_role(db, seeded, "process.engineer.matspec", "Process Engineer")
    token = await login(client, "process.engineer.matspec")

    resp = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id, "MATSPEC-2", acceptance_criteria={"assay_min": "98.0"}),
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    version_id = resp.json()["aggregate_id"]

    detail = await client.get(f"/material-specifications/v1/{version_id}", headers=auth_headers(token))
    assert detail.status_code == 200
    body = detail.json()
    assert body["material_spec_business_id"] == "MATSPEC-2"
    assert body["lifecycle_state"] == "draft"
    assert body["acceptance_criteria"] == {"assay_min": "98.0"}

    versions = await client.get("/material-specifications/v1/MATSPEC-2/versions", headers=auth_headers(token))
    assert versions.status_code == 200
    assert len(versions.json()) == 1


async def test_create_draft_rejects_duplicate_business_id_version_no(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-TEST-003")
        await _make_user_with_role(db, seeded, "process.engineer.matspec2", "Process Engineer")
    token = await login(client, "process.engineer.matspec2")

    first = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id, "MATSPEC-3"),
        headers=auth_headers(token),
    )
    assert first.status_code == 200

    second = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id, "MATSPEC-3"),
        headers=auth_headers(token),
    )
    assert second.status_code == 422
    assert second.json()["code"] == "VALIDATION_FAILED"


async def test_create_draft_rejects_unknown_material_id(client, seeded, db):
    async with db.begin():
        await _make_user_with_role(db, seeded, "process.engineer.matspec3", "Process Engineer")
    token = await login(client, "process.engineer.matspec3")

    resp = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], uuid.uuid4(), "MATSPEC-4"),
        headers=auth_headers(token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


async def test_release_fails_closed_with_no_signature_policy(client, seeded, db):
    """No SignaturePolicy row is added by conftest.py's global fixture set for
    material_specification_version/release (the real row now lives in scripts/seed.py's
    SIGNATURE_POLICY_FLOOR for the live DB, SG-185 RESOLVED 2026-09-18) -- so absent a local row like the
    one the test below adds, resolve_signature_requirement() still correctly fails closed with
    SIGNATURE_POLICY_UNRESOLVED, proving the fail-closed path itself still works."""
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-TEST-005")
        await _make_user_with_role(db, seeded, "process.engineer.matspec5", "Process Engineer")
        await _make_user_with_role(db, seeded, "qa.releaser.matspec5", "QA Releaser")
    author_token = await login(client, "process.engineer.matspec5")
    releaser_token = await login(client, "qa.releaser.matspec5")

    create = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id, "MATSPEC-5"),
        headers=auth_headers(author_token),
    )
    assert create.status_code == 200
    version_id = create.json()["aggregate_id"]

    release = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release",
        json={
            "idempotency_key": idem(), "material_spec_version_id": version_id, "expected_version": 1,
        },
        headers=auth_headers(releaser_token),
    )
    assert release.status_code == 409
    assert release.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_release_authored_by_process_engineer_is_released_by_an_independent_qa_releaser(client, seeded, db):
    """SG-185 RESOLVED (2026-09-18, project-owner-directed): same independence shape as
    test_product_master.py's product_version equivalent -- Process Engineer holds material_spec.author
    (not .release); QA Releaser holds material_spec.release; the release signature policy adds
    person-level independence (author != releaser -> SOD_CONFLICT), enforced in
    release_material_spec_version()."""
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-TEST-007")
        dual = await _make_user_with_role(db, seeded, "dual.matspec", "Process Engineer")
        db.add(UserSiteRole(user_id=dual.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        await _make_user_with_role(db, seeded, "pe.matspec7", "Process Engineer")
        await _make_user_with_role(db, seeded, "releaser.matspec7", "QA Releaser")
        db.add(
            SignaturePolicy(
                record_type="material_specification_version", action="release", meaning="Released",
                required_role_id=seeded["roles"]["QA Releaser"].id, requires_independent_signer=True,
                signature_required=True, policy_source="PLATFORM_FLOOR",
            )
        )
    pe_token = await login(client, "pe.matspec7")
    dual_token = await login(client, "dual.matspec")
    releaser_token = await login(client, "releaser.matspec7")

    version_id = (
        await client.post(
            "/material-specifications/v1/drafts",
            json=_draft_body(seeded["site_id"], material.id, "MATSPEC-7"),
            headers=auth_headers(pe_token),
        )
    ).json()["aggregate_id"]
    body = {"idempotency_key": idem(), "material_spec_version_id": version_id, "expected_version": 1}

    # Process Engineer cannot release (no material_spec.release permission -> router gate).
    resp = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release", json=body, headers=auth_headers(pe_token)
    )
    assert resp.status_code == 403 and resp.json()["code"] == "ROLE_MISSING"

    # The dual-role user releasing a spec THEY authored -> independence blocks it.
    version_id2 = (
        await client.post(
            "/material-specifications/v1/drafts",
            json=_draft_body(seeded["site_id"], material.id, "MATSPEC-7-DUAL"),
            headers=auth_headers(dual_token),
        )
    ).json()["aggregate_id"]
    resp = await client.post(
        f"/material-specifications/v1/drafts/{version_id2}/release",
        json={"idempotency_key": idem(), "material_spec_version_id": version_id2, "expected_version": 1},
        headers=auth_headers(dual_token),
    )
    assert resp.status_code == 409 and resp.json()["code"] == "SOD_CONFLICT"

    # Independent QA Releaser: unsigned -> 428, signed -> released.
    resp = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release",
        json={**body, "idempotency_key": idem()}, headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 428
    ch = (
        await client.post(
            f"/material-specifications/v1/{version_id}/signature-challenges",
            json={"action": "release"}, headers=auth_headers(releaser_token),
        )
    ).json()
    resp = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release",
        json={**body, "idempotency_key": idem(), "challenge_id": ch["challenge_id"], "reauth_password": DEMO_PASSWORD},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    assert (
        await client.get(f"/material-specifications/v1/{version_id}", headers=auth_headers(releaser_token))
    ).json()["lifecycle_state"] == "released"


async def test_release_requires_material_spec_release_permission(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-TEST-006")
        await _make_user_with_role(db, seeded, "process.engineer.matspec6", "Process Engineer")
    token = await login(client, "process.engineer.matspec6")

    create = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id, "MATSPEC-6"),
        headers=auth_headers(token),
    )
    assert create.status_code == 200
    version_id = create.json()["aggregate_id"]

    # Process Engineer holds material_spec.author, not .release (author != releaser, same split as
    # product_version/recipe_version).
    release = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "material_spec_version_id": version_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert release.status_code == 403
    assert release.json()["code"] == "ROLE_MISSING"
