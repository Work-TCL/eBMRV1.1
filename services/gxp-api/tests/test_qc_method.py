"""SG-066 (QC-FR-003/004) -- draft/release for the new, additive QcMethodVersion (Document 23's
Method-master entity, never defined by the spec itself). Release intentionally has no Document 106
policy row yet and must fail closed with SIGNATURE_POLICY_UNRESOLVED (SG-186) -- same state every other
brand-new record type in this codebase was correctly left in before its own resolution.
"""

import uuid

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.product_master.models import ProductVersion
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_user(db, seeded, username, role_name):
    user = User(
        username=username, email=f"{username}@example.com", full_name=username,
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


def _draft_body(site_id, method_code="MTH-1", **overrides):
    body = {
        "idempotency_key": idem(),
        "method_code": method_code,
        "method_type": "compendial",
        "name": "USP <711> Dissolution",
        "site_id": str(site_id),
    }
    body.update(overrides)
    return body


async def test_create_draft_requires_qc_method_author_permission(client, seeded, db):
    async with db.begin():
        await _make_user(db, seeded, "qa.releaser.qcm1", "QA Releaser")
    token = await login(client, "qa.releaser.qcm1")
    resp = await client.post("/qc/v1/methods/drafts", json=_draft_body(seeded["site_id"]), headers=auth_headers(token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post(
        "/qc/v1/methods/drafts", json={"idempotency_key": idem(), "method_code": "X"}, headers={}
    )
    assert resp.status_code == 401


async def test_create_draft_succeeds_for_qc_reviewer_and_is_readable(client, seeded, db):
    async with db.begin():
        await _make_user(db, seeded, "qc.reviewer.qcm1", "QC Reviewer")
    token = await login(client, "qc.reviewer.qcm1")

    resp = await client.post(
        "/qc/v1/methods/drafts",
        json=_draft_body(seeded["site_id"], "MTH-2", validation_evidence_reference="VAL-REPORT-002"),
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    version_id = resp.json()["aggregate_id"]

    detail = await client.get(f"/qc/v1/methods/{version_id}", headers=auth_headers(token))
    assert detail.status_code == 200
    body = detail.json()
    assert body["method_code"] == "MTH-2"
    assert body["lifecycle_state"] == "draft"
    assert body["validation_evidence_reference"] == "VAL-REPORT-002"

    versions = await client.get("/qc/v1/methods/MTH-2/versions", headers=auth_headers(token))
    assert versions.status_code == 200
    assert len(versions.json()) == 1


async def test_create_draft_rejects_unknown_method_type(client, seeded, db):
    async with db.begin():
        await _make_user(db, seeded, "qc.reviewer.qcm2", "QC Reviewer")
    token = await login(client, "qc.reviewer.qcm2")

    resp = await client.post(
        "/qc/v1/methods/drafts",
        json=_draft_body(seeded["site_id"], "MTH-3", method_type="homemade"),
        headers=auth_headers(token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_second_version_requires_modification_reason(client, seeded, db):
    """QC-FR-004: a modified method requires a controlled version, reason, validation/suitability
    evidence and approval; original method remains."""
    async with db.begin():
        await _make_user(db, seeded, "qc.reviewer.qcm3", "QC Reviewer")
    token = await login(client, "qc.reviewer.qcm3")

    first = await client.post(
        "/qc/v1/methods/drafts", json=_draft_body(seeded["site_id"], "MTH-4"), headers=auth_headers(token)
    )
    assert first.status_code == 200

    second_no_reason = await client.post(
        "/qc/v1/methods/drafts", json=_draft_body(seeded["site_id"], "MTH-4"), headers=auth_headers(token)
    )
    assert second_no_reason.status_code == 422
    assert second_no_reason.json()["code"] == "VALIDATION_FAILED"

    second_with_reason = await client.post(
        "/qc/v1/methods/drafts",
        json=_draft_body(seeded["site_id"], "MTH-4", modification_reason="Improved column temperature control"),
        headers=auth_headers(token),
    )
    assert second_with_reason.status_code == 200, second_with_reason.text

    versions = (await client.get("/qc/v1/methods/MTH-4/versions", headers=auth_headers(token))).json()
    assert len(versions) == 2
    assert versions[0]["version_no"] == 1
    assert versions[1]["version_no"] == 2
    assert versions[1]["modification_reason"] == "Improved column temperature control"
    # The original version is retained, not edited.
    assert versions[0]["modification_reason"] is None


async def test_release_fails_closed_with_no_signature_policy(client, seeded, db):
    async with db.begin():
        await _make_user(db, seeded, "qc.reviewer.qcm5", "QC Reviewer")
        await _make_user(db, seeded, "qa.releaser.qcm5", "QA Releaser")
    author_token = await login(client, "qc.reviewer.qcm5")
    releaser_token = await login(client, "qa.releaser.qcm5")

    create = await client.post(
        "/qc/v1/methods/drafts", json=_draft_body(seeded["site_id"], "MTH-5"), headers=auth_headers(author_token)
    )
    assert create.status_code == 200
    version_id = create.json()["aggregate_id"]

    release = await client.post(
        f"/qc/v1/methods/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "method_version_id": version_id, "expected_version": 1},
        headers=auth_headers(releaser_token),
    )
    assert release.status_code == 409
    assert release.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_release_requires_qc_method_release_permission(client, seeded, db):
    async with db.begin():
        await _make_user(db, seeded, "qc.reviewer.qcm6", "QC Reviewer")
    token = await login(client, "qc.reviewer.qcm6")

    create = await client.post(
        "/qc/v1/methods/drafts", json=_draft_body(seeded["site_id"], "MTH-6"), headers=auth_headers(token)
    )
    assert create.status_code == 200
    version_id = create.json()["aggregate_id"]

    # QC Reviewer holds qc_method.author, not .release (author != releaser).
    release = await client.post(
        f"/qc/v1/methods/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "method_version_id": version_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert release.status_code == 403
    assert release.json()["code"] == "ROLE_MISSING"


async def test_test_definition_can_reference_a_real_method_version(client, seeded, db):
    async with db.begin():
        pv = ProductVersion(
            product_business_id="QCM-PROD-1", version_no=1, product_code="QCM-PROD-1", name="QC Method Test Product",
            manufacturing_profile_code="oral_solid", lifecycle_state="released", site_id=seeded["site_id"],
        )
        db.add(pv)
        await db.flush()
        await _make_user(db, seeded, "qc.reviewer.qcm7", "QC Reviewer")
    token = await login(client, "qc.reviewer.qcm7")

    method = await client.post(
        "/qc/v1/methods/drafts", json=_draft_body(seeded["site_id"], "MTH-7"), headers=auth_headers(token)
    )
    assert method.status_code == 200
    method_version_id = method.json()["aggregate_id"]

    spec = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "QCM-SPEC-7", "scope_type": "product",
            "scope_version_id": str(pv.id),
            "test_definitions": [
                {
                    "test_code": "ASSAY", "test_name": "Assay", "method_version_id": method_version_id,
                    "result_data_type": "numeric",
                }
            ],
        },
        headers=auth_headers(token),
    )
    assert spec.status_code == 200, spec.text


async def test_test_definition_rejects_unknown_method_version_id(client, seeded, db):
    async with db.begin():
        pv = ProductVersion(
            product_business_id="QCM-PROD-2", version_no=1, product_code="QCM-PROD-2", name="QC Method Test Product 2",
            manufacturing_profile_code="oral_solid", lifecycle_state="released", site_id=seeded["site_id"],
        )
        db.add(pv)
        await db.flush()
        await _make_user(db, seeded, "qc.reviewer.qcm8", "QC Reviewer")
    token = await login(client, "qc.reviewer.qcm8")

    spec = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "QCM-SPEC-8", "scope_type": "product",
            "scope_version_id": str(pv.id),
            "test_definitions": [
                {
                    "test_code": "ASSAY", "test_name": "Assay", "method_version_id": str(uuid.uuid4()),
                    "result_data_type": "numeric",
                }
            ],
        },
        headers=auth_headers(token),
    )
    assert spec.status_code == 404
    assert spec.json()["code"] == "NOT_FOUND"


async def test_release_rejects_stale_expected_version(client, seeded, db):
    async with db.begin():
        await _make_user(db, seeded, "qc.reviewer.qcm9", "QC Reviewer")
        await _make_user(db, seeded, "qa.releaser.qcm9", "QA Releaser")
    author_token = await login(client, "qc.reviewer.qcm9")
    releaser_token = await login(client, "qa.releaser.qcm9")

    create = await client.post(
        "/qc/v1/methods/drafts", json=_draft_body(seeded["site_id"], "MTH-9"), headers=auth_headers(author_token)
    )
    assert create.status_code == 200
    version_id = create.json()["aggregate_id"]

    release = await client.post(
        f"/qc/v1/methods/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "method_version_id": version_id, "expected_version": 99},
        headers=auth_headers(releaser_token),
    )
    assert release.status_code == 409
    assert release.json()["code"] == "STALE_VERSION"
