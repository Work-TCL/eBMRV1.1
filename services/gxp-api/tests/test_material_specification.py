"""SG-057 (architecture rule C-014) -- draft/release for the new, additive MaterialSpecificationVersion
module. Release now resolves to a real signature policy (SG-185 RESOLVED 2026-09-18,
project-owner-directed: same shape as product_version/release -- "Released" by an independent QA
Releaser).
"""

import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.material.models import Material
from app.modules.qc.models import QcTestDefinition, QcTestSpecification
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


def _draft_body(site_id, material_id, **overrides):
    # Client gap-analysis Phase 5 (2026-10-05): material_spec_business_id is no longer a caller-supplied
    # field (client found it confusing) -- it's derived server-side from the material's own `code` as
    # f"{material.code}-SPEC", and version_no defaults to the next available one when omitted.
    body = {
        "idempotency_key": idem(),
        "material_id": str(material_id),
        "name": "Test Material Specification",
        "site_id": str(site_id),
    }
    body.update(overrides)
    return body


def _expected_business_id(material_code: str) -> str:
    return f"{material_code}-SPEC"


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
        json=_draft_body(seeded["site_id"], material.id),
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    version_id = resp.json()["aggregate_id"]

    expected_business_id = _expected_business_id(material.code)
    detail = await client.get(f"/material-specifications/v1/{version_id}", headers=auth_headers(token))
    assert detail.status_code == 200
    body = detail.json()
    assert body["material_spec_business_id"] == expected_business_id
    assert body["version_no"] == 1  # auto-computed, none existed yet for this material
    assert body["lifecycle_state"] == "draft"
    assert body["criteria"] == []

    versions = await client.get(f"/material-specifications/v1/{expected_business_id}/versions", headers=auth_headers(token))
    assert versions.status_code == 200
    assert len(versions.json()) == 1


async def test_create_draft_rejects_duplicate_business_id_version_no(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-TEST-003")
        await _make_user_with_role(db, seeded, "process.engineer.matspec2", "Process Engineer")
    token = await login(client, "process.engineer.matspec2")

    first = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id),
        headers=auth_headers(token),
    )
    assert first.status_code == 200

    # version_no omitted above auto-computed to 1; a second create for the same material with no
    # override would auto-advance to 2 (not a collision at all) -- explicitly repeat version_no=1 here to
    # exercise the actual conflict-rejection path.
    second = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id, version_no=1),
        headers=auth_headers(token),
    )
    assert second.status_code == 422
    assert second.json()["code"] == "VALIDATION_FAILED"


async def test_create_draft_auto_increments_version_no_when_omitted(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-TEST-003B")
        await _make_user_with_role(db, seeded, "process.engineer.matspec2b", "Process Engineer")
    token = await login(client, "process.engineer.matspec2b")

    first = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id),
        headers=auth_headers(token),
    )
    assert first.status_code == 200
    first_id = first.json()["aggregate_id"]
    assert (
        await client.get(f"/material-specifications/v1/{first_id}", headers=auth_headers(token))
    ).json()["version_no"] == 1

    second = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], material.id),
        headers=auth_headers(token),
    )
    assert second.status_code == 200, second.text
    second_id = second.json()["aggregate_id"]
    second_detail = (
        await client.get(f"/material-specifications/v1/{second_id}", headers=auth_headers(token))
    ).json()
    assert second_detail["version_no"] == 2
    assert second_detail["material_spec_business_id"] == _expected_business_id(material.code)


async def test_create_draft_rejects_unknown_material_id(client, seeded, db):
    async with db.begin():
        await _make_user_with_role(db, seeded, "process.engineer.matspec3", "Process Engineer")
    token = await login(client, "process.engineer.matspec3")

    resp = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(seeded["site_id"], uuid.uuid4()),
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
        json=_draft_body(seeded["site_id"], material.id),
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
            json=_draft_body(seeded["site_id"], material.id),
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
            json=_draft_body(seeded["site_id"], material.id),
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
        json=_draft_body(seeded["site_id"], material.id),
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


# ---------------------------------------------------------------------------
# Specification criteria -- client gap-analysis Phase 5 (2026-10-05).
# ---------------------------------------------------------------------------


def _criterion_body(version_id, **overrides):
    body = {
        "idempotency_key": idem(),
        "material_spec_version_id": str(version_id),
        "test_name": "Assay",
        "specification_text": "98.0 to 102.0%",
        "acceptance_criteria_text": "98.0 to 102.0%",
        "fulfillment_path": "in_house",
    }
    body.update(overrides)
    return body


async def _create_draft_as(client, token, site_id, material_id) -> str:
    resp = await client.post(
        "/material-specifications/v1/drafts",
        json=_draft_body(site_id, material_id),
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_add_criterion_appears_on_draft_detail_in_sequence(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-CRIT-001")
        await _make_user_with_role(db, seeded, "pe.crit1", "Process Engineer")
    token = await login(client, "pe.crit1")
    version_id = await _create_draft_as(client, token, seeded["site_id"], material.id)

    first = await client.post(
        "/material-specifications/v1/criteria",
        json=_criterion_body(version_id, test_name="Assay"),
        headers=auth_headers(token),
    )
    assert first.status_code == 200, first.text
    second = await client.post(
        "/material-specifications/v1/criteria",
        json=_criterion_body(version_id, test_name="Appearance", fulfillment_path="supplier_coa"),
        headers=auth_headers(token),
    )
    assert second.status_code == 200, second.text

    detail = (
        await client.get(f"/material-specifications/v1/{version_id}", headers=auth_headers(token))
    ).json()
    assert len(detail["criteria"]) == 2
    assert detail["criteria"][0]["sequence"] == 1
    assert detail["criteria"][0]["test_name"] == "Assay"
    assert detail["criteria"][1]["sequence"] == 2
    assert detail["criteria"][1]["test_name"] == "Appearance"
    assert detail["criteria"][1]["fulfillment_path"] == "supplier_coa"


async def test_add_criterion_rejects_unknown_fulfillment_path(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-CRIT-002")
        await _make_user_with_role(db, seeded, "pe.crit2", "Process Engineer")
    token = await login(client, "pe.crit2")
    version_id = await _create_draft_as(client, token, seeded["site_id"], material.id)

    resp = await client.post(
        "/material-specifications/v1/criteria",
        json=_criterion_body(version_id, fulfillment_path="carrier_pigeon"),
        headers=auth_headers(token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_add_criterion_requires_material_spec_author_permission(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-CRIT-003")
        await _make_user_with_role(db, seeded, "pe.crit3", "Process Engineer")
        await _make_user_with_role(db, seeded, "qa.reviewer.crit3", "QA Reviewer")
    author_token = await login(client, "pe.crit3")
    other_token = await login(client, "qa.reviewer.crit3")
    version_id = await _create_draft_as(client, author_token, seeded["site_id"], material.id)

    resp = await client.post(
        "/material-specifications/v1/criteria",
        json=_criterion_body(version_id),
        headers=auth_headers(other_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_update_and_remove_criterion(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-CRIT-004")
        await _make_user_with_role(db, seeded, "pe.crit4", "Process Engineer")
    token = await login(client, "pe.crit4")
    version_id = await _create_draft_as(client, token, seeded["site_id"], material.id)

    add_resp = await client.post(
        "/material-specifications/v1/criteria", json=_criterion_body(version_id), headers=auth_headers(token)
    )
    criterion_id = add_resp.json()["aggregate_id"]

    update_resp = await client.patch(
        f"/material-specifications/v1/criteria/{criterion_id}",
        json={
            "idempotency_key": idem(), "criterion_id": criterion_id, "expected_version": 1,
            "test_name": "Assay (revised)", "specification_text": "97.0 to 103.0%",
            "acceptance_criteria_text": "97.0 to 103.0%", "fulfillment_path": "external_lab",
        },
        headers=auth_headers(token),
    )
    assert update_resp.status_code == 200, update_resp.text

    detail = (
        await client.get(f"/material-specifications/v1/{version_id}", headers=auth_headers(token))
    ).json()
    assert detail["criteria"][0]["test_name"] == "Assay (revised)"
    assert detail["criteria"][0]["fulfillment_path"] == "external_lab"

    remove_resp = await client.request(
        "DELETE",
        f"/material-specifications/v1/criteria/{criterion_id}",
        json={"idempotency_key": idem(), "criterion_id": criterion_id},
        headers=auth_headers(token),
    )
    assert remove_resp.status_code == 200, remove_resp.text

    detail_after = (
        await client.get(f"/material-specifications/v1/{version_id}", headers=auth_headers(token))
    ).json()
    assert detail_after["criteria"] == []


async def test_criteria_locked_once_version_is_released(client, seeded, db):
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-CRIT-005")
        dual = await _make_user_with_role(db, seeded, "dual.crit5", "Process Engineer")
        db.add(UserSiteRole(user_id=dual.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        db.add(
            SignaturePolicy(
                record_type="material_specification_version", action="release", meaning="Released",
                required_role_id=seeded["roles"]["QA Releaser"].id, requires_independent_signer=False,
                signature_required=False, policy_source="PLATFORM_FLOOR",
            )
        )
    token = await login(client, "dual.crit5")
    version_id = await _create_draft_as(client, token, seeded["site_id"], material.id)

    add_resp = await client.post(
        "/material-specifications/v1/criteria", json=_criterion_body(version_id), headers=auth_headers(token)
    )
    criterion_id = add_resp.json()["aggregate_id"]

    release_resp = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "material_spec_version_id": version_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert release_resp.status_code == 200, release_resp.text

    # The released snapshot carries the criteria that existed at release time.
    detail = (
        await client.get(f"/material-specifications/v1/{version_id}", headers=auth_headers(token))
    ).json()
    assert detail["lifecycle_state"] == "released"
    assert len(detail["criteria"]) == 1

    # No further add/update/remove is permitted once released.
    add_after = await client.post(
        "/material-specifications/v1/criteria", json=_criterion_body(version_id), headers=auth_headers(token)
    )
    assert add_after.status_code == 409
    assert add_after.json()["code"] == "INVALID_TRANSITION"

    remove_after = await client.request(
        "DELETE",
        f"/material-specifications/v1/criteria/{criterion_id}",
        json={"idempotency_key": idem(), "criterion_id": criterion_id},
        headers=auth_headers(token),
    )
    assert remove_after.status_code == 409
    assert remove_after.json()["code"] == "INVALID_TRANSITION"


async def test_release_auto_drafts_qc_test_specification_for_testable_criteria(client, seeded, db):
    """Client gap-analysis Phase 6 (2026-10-05): releasing a version with in_house/external_lab criteria
    now drafts a matching QcTestSpecification/QcTestDefinition (required+release_blocking) scoped to this
    exact version, bridging into the real QC release-gating pipeline
    (material.commands._missing_required_tests) that nothing previously populated. A supplier_coa
    criterion is deliberately skipped -- that case is already covered by the existing lot-level
    `coa_reliance` override (migration 0126), not by scheduling a test. The draft is NOT auto-released
    (AG-07/SIG-FR-006: still requires a human QA signature via the normal QC Specifications screen)."""
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-QCBRIDGE-001")
        dual = await _make_user_with_role(db, seeded, "dual.qcbridge1", "Process Engineer")
        db.add(UserSiteRole(user_id=dual.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        db.add(
            SignaturePolicy(
                record_type="material_specification_version", action="release", meaning="Released",
                required_role_id=seeded["roles"]["QA Releaser"].id, requires_independent_signer=False,
                signature_required=False, policy_source="PLATFORM_FLOOR",
            )
        )
    token = await login(client, "dual.qcbridge1")
    version_id = await _create_draft_as(client, token, seeded["site_id"], material.id)

    for name, path in (("Assay", "in_house"), ("Heavy Metals", "external_lab"), ("Appearance", "supplier_coa")):
        resp = await client.post(
            "/material-specifications/v1/criteria",
            json=_criterion_body(version_id, test_name=name, fulfillment_path=path),
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text

    release_resp = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "material_spec_version_id": version_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert release_resp.status_code == 200, release_resp.text

    spec = (
        await db.execute(
            select(QcTestSpecification).where(
                QcTestSpecification.scope_type == "material",
                QcTestSpecification.scope_version_id == uuid.UUID(version_id),
            )
        )
    ).scalar_one()
    assert spec.status == "draft"

    definitions = (
        await db.execute(select(QcTestDefinition).where(QcTestDefinition.specification_id == spec.id))
    ).scalars().all()
    assert {d.test_name for d in definitions} == {"Assay", "Heavy Metals"}
    for d in definitions:
        assert d.required is True
        assert d.release_blocking is True


async def test_release_skips_qc_sync_when_no_testable_criteria(client, seeded, db):
    """A version with only a supplier_coa criterion (or none at all) must not create an empty/pointless
    QcTestSpecification draft."""
    async with db.begin():
        material = await _make_material(db, seeded, "MAT-SPEC-QCBRIDGE-002")
        dual = await _make_user_with_role(db, seeded, "dual.qcbridge2", "Process Engineer")
        db.add(UserSiteRole(user_id=dual.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        db.add(
            SignaturePolicy(
                record_type="material_specification_version", action="release", meaning="Released",
                required_role_id=seeded["roles"]["QA Releaser"].id, requires_independent_signer=False,
                signature_required=False, policy_source="PLATFORM_FLOOR",
            )
        )
    token = await login(client, "dual.qcbridge2")
    version_id = await _create_draft_as(client, token, seeded["site_id"], material.id)
    resp = await client.post(
        "/material-specifications/v1/criteria",
        json=_criterion_body(version_id, test_name="Appearance", fulfillment_path="supplier_coa"),
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    release_resp = await client.post(
        f"/material-specifications/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "material_spec_version_id": version_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert release_resp.status_code == 200, release_resp.text

    spec = (
        await db.execute(
            select(QcTestSpecification).where(
                QcTestSpecification.scope_type == "material",
                QcTestSpecification.scope_version_id == uuid.UUID(version_id),
            )
        )
    ).scalar_one_or_none()
    assert spec is None
