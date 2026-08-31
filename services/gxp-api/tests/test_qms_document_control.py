"""Document 30 (SPEC-QMS-005) -- the buildable slice: the linear DRAFT -> REVIEW -> RELEASED -> EFFECTIVE
-> OBSOLETE pipeline, matching the module's own 7-op API list exactly (`/documents/v1` prefix). New module.
DOC-FR-011/013/014/022/023(partial)/024 are out of scope this pass -- see docs/generated/18_SPEC_GAPS.md
SG-078/SG-079/SG-080.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
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
        owner = await _make_admin(db, seeded, f"admin.doc{tag}")
        db.add(SignaturePolicy(record_type="controlled_document_version", action="release", meaning="Approved", signature_required=signed))
    return owner


def _create_body(site_id, owner_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "document_code": f"SOP-{uuid.uuid4().hex[:8]}",
        "document_type": "sop", "owner_subject_id": str(owner_id), "version_label": "1.0",
        "content_hash": "a" * 64,
    }
    body.update(overrides)
    return body


async def _create(client, token, site_id, owner_id, **overrides):
    resp = await client.post("/documents/v1/drafts", json=_create_body(site_id, owner_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _advance_to_released(client, token, version_id, **release_overrides):
    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/submit",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 1, "reviewers": [{"role": "technical", "subject_id": str(uuid.uuid4())}]},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 1 -> 2

    body = {"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 2, "review_completed": True}
    body.update(release_overrides)
    resp = await client.post(f"/documents/v1/drafts/{version_id}/release", json=body, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text  # version 2 -> 3
    return 3


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/documents/v1/drafts", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_rejects_unrecognized_document_type(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.doc1")
    resp = await client.post(
        "/documents/v1/drafts", json=_create_body(seeded["site_id"], owner.id, document_type="not_a_real_type"), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_full_lifecycle_to_obsolete(client, seeded, db):
    owner = await _setup(db, seeded, "2", signed=False)
    token = await login(client, "admin.doc2")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_released(client, token, version_id)

    resp = await client.post(
        f"/documents/v1/versions/{version_id}/make-effective",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": next_version},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/documents/v1/versions/{version_id}/obsolete",
        json={
            "idempotency_key": idem(), "document_version_id": version_id, "expected_version": next_version,
            "retirement_reason": "superseded by revised procedure", "retire_document": True,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms.document_models import ControlledDocument, ControlledDocumentVersion
    version = await db.get(ControlledDocumentVersion, uuid.UUID(version_id))
    assert version.state == "OBSOLETE"
    document = await db.get(ControlledDocument, version.document_id)
    assert document.status == "retired"


async def test_release_requires_review_confirmation(client, seeded, db):
    owner = await _setup(db, seeded, "3")
    token = await login(client, "admin.doc3")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    await client.post(
        f"/documents/v1/drafts/{version_id}/submit",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 1, "reviewers": [{"role": "technical", "subject_id": str(uuid.uuid4())}]},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 2, "review_completed": False},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "DOCUMENT_REVIEW_INCOMPLETE"


async def test_release_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "4", signed=True)
    token = await login(client, "admin.doc4")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    await client.post(
        f"/documents/v1/drafts/{version_id}/submit",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 1, "reviewers": [{"role": "technical", "subject_id": str(uuid.uuid4())}]},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/release",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 2, "review_completed": True},
        headers=auth_headers(token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "DOCUMENT_SIGNATURE_REQUIRED"


async def test_make_effective_rejects_future_effective_date(client, seeded, db):
    owner = await _setup(db, seeded, "5")
    token = await login(client, "admin.doc5")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    future = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    next_version = await _advance_to_released(client, token, version_id, effective_from=future)
    resp = await client.post(
        f"/documents/v1/versions/{version_id}/make-effective",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": next_version},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "EFFECTIVE_PREREQUISITES_INCOMPLETE"


async def test_make_effective_requires_training_confirmation(client, seeded, db):
    owner = await _setup(db, seeded, "6")
    token = await login(client, "admin.doc6")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_released(client, token, version_id, training_impact={"required": True})
    resp = await client.post(
        f"/documents/v1/versions/{version_id}/make-effective",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": next_version},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "EFFECTIVE_PREREQUISITES_INCOMPLETE"


async def test_supersession_on_second_effective_version(client, seeded, db):
    owner = await _setup(db, seeded, "7", signed=False)
    token = await login(client, "admin.doc7")
    code = f"SOP-{uuid.uuid4().hex[:8]}"
    v1_id = await _create(client, token, seeded["site_id"], owner.id, document_code=code, version_label="1.0")
    next_version = await _advance_to_released(client, token, v1_id)
    resp = await client.post(
        f"/documents/v1/versions/{v1_id}/make-effective",
        json={"idempotency_key": idem(), "document_version_id": v1_id, "expected_version": next_version},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    v2_id = await _create(client, token, seeded["site_id"], owner.id, document_code=code, version_label="2.0")
    next_version = await _advance_to_released(client, token, v2_id)
    resp = await client.post(
        f"/documents/v1/versions/{v2_id}/make-effective",
        json={"idempotency_key": idem(), "document_version_id": v2_id, "expected_version": next_version},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms.document_models import ControlledDocumentVersion
    v1 = await db.get(ControlledDocumentVersion, uuid.UUID(v1_id))
    v2 = await db.get(ControlledDocumentVersion, uuid.UUID(v2_id))
    assert v1.state == "SUPERSEDED"
    assert v1.superseded_by_version_id == v2.id
    assert v2.state == "EFFECTIVE"


async def test_controlled_copy_issuance_and_conflict(client, seeded, db):
    owner = await _setup(db, seeded, "8", signed=False)
    token = await login(client, "admin.doc8")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_released(client, token, version_id)
    resp = await client.post(
        f"/documents/v1/versions/{version_id}/make-effective",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": next_version},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/documents/v1/versions/{version_id}/controlled-copies",
        json={
            "idempotency_key": idem(), "document_version_id": version_id, "expected_version": next_version,
            "copy_number": "CC-001", "recipient": "Production Floor Binder 3",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/documents/v1/versions/{version_id}/controlled-copies",
        json={
            "idempotency_key": idem(), "document_version_id": version_id, "expected_version": next_version,
            "copy_number": "CC-001", "recipient": "Warehouse Binder 1",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "CONTROLLED_COPY_CONFLICT"


async def test_controlled_copy_rejected_for_non_effective_version(client, seeded, db):
    owner = await _setup(db, seeded, "9")
    token = await login(client, "admin.doc9")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/documents/v1/versions/{version_id}/controlled-copies",
        json={
            "idempotency_key": idem(), "document_version_id": version_id, "expected_version": 1,
            "copy_number": "CC-001", "recipient": "Production Floor",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "DOCUMENT_VERSION_OBSOLETE"


async def test_release_with_unknown_change_control_id_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "10")
    token = await login(client, "admin.doc10")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    await client.post(
        f"/documents/v1/drafts/{version_id}/submit",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 1, "reviewers": [{"role": "technical", "subject_id": str(uuid.uuid4())}]},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/release",
        json={
            "idempotency_key": idem(), "document_version_id": version_id, "expected_version": 2,
            "review_completed": True, "change_control_id": str(uuid.uuid4()),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "NOT_FOUND"


async def test_get_versions_lists_all_versions_for_code(client, seeded, db):
    owner = await _setup(db, seeded, "11", signed=False)
    token = await login(client, "admin.doc11")
    code = f"SOP-{uuid.uuid4().hex[:8]}"
    v1_id = await _create(client, token, seeded["site_id"], owner.id, document_code=code, version_label="1.0")
    await _create(client, token, seeded["site_id"], owner.id, document_code=code, version_label="2.0")

    resp = await client.get(f"/documents/v1/{code}/versions", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["document_code"] == code
    assert len(body["versions"]) == 2
    assert {v["version_label"] for v in body["versions"]} == {"1.0", "2.0"}


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "12")
    token = await login(client, "admin.doc12")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/submit",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 99, "reviewers": [{"role": "technical", "subject_id": str(uuid.uuid4())}]},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "13")
    token = await login(client, "admin.doc13")
    key = idem()
    body = _create_body(seeded["site_id"], owner.id)
    body["idempotency_key"] = key
    resp1 = await client.post("/documents/v1/drafts", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/documents/v1/drafts", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_duplicate_idempotency_key_different_payload_conflicts(client, seeded, db):
    owner = await _setup(db, seeded, "14")
    token = await login(client, "admin.doc14")
    key = idem()
    body1 = _create_body(seeded["site_id"], owner.id, document_code="SOP-IDEM-A")
    body1["idempotency_key"] = key
    resp1 = await client.post("/documents/v1/drafts", json=body1, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    body2 = _create_body(seeded["site_id"], owner.id, document_code="SOP-IDEM-B")
    body2["idempotency_key"] = key
    resp2 = await client.post("/documents/v1/drafts", json=body2, headers=auth_headers(token))
    assert resp2.status_code == 409, resp2.text
    assert resp2.json()["code"] == "IDEMPOTENCY_CONFLICT"


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.doc20")
    token = await login(client, "admin.doc20")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/signature-challenges", json={"action": "release"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_version(client, seeded, db):
    owner = await _setup(db, seeded, "21")
    token = await login(client, "admin.doc21")
    resp = await client.post(
        f"/documents/v1/drafts/{uuid.uuid4()}/signature-challenges", json={"action": "release"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_release(client, seeded, db):
    owner = await _setup(db, seeded, "22", signed=True)
    token = await login(client, "admin.doc22")
    version_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/submit",
        json={"idempotency_key": idem(), "document_version_id": version_id, "expected_version": 1, "reviewers": [{"role": "technical", "subject_id": str(uuid.uuid4())}]},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 1 -> 2

    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/signature-challenges", json={"action": "release"}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Approved"

    resp = await client.post(
        f"/documents/v1/drafts/{version_id}/release",
        json={
            "idempotency_key": idem(), "document_version_id": version_id, "expected_version": 2, "review_completed": True,
            "challenge_id": body["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
