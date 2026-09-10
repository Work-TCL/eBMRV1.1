"""Document 06 (SPEC-GXP-004) — vault release/integrity/correction. Covers what's achievable against the
now-real integration into release_batch/disposition_material_lot: a release creates a correctly-hashed,
version-incrementing snapshot; tampering is detectable; the generic release/correction-completion
endpoints correctly fail closed (no Document 106 policy row exists for either yet — same honest pattern
as Document 05's export); permission/authorization boundaries are real.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.vault import service as vault_service
from app.modules.vault.models import VaultObject
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_batch_flow import _walk_batch_to_release_ready


async def _make_admin(db, seeded, username="admin.vault"):
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


async def test_release_batch_creates_vault_snapshot(client, seeded, db):
    op_token = await login(client, "operator1")
    reviewer_token = await login(client, "qa.reviewer")
    releaser_token = await login(client, "qa.releaser")
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.vault")

    batch_id = await _walk_batch_to_release_ready(
        client, op_token, reviewer_token, seeded["site_id"], "B-VAULT"
    )
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(releaser_token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/release",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 8,
            "decision": "released",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    batch_number = (await client.get(f"/batches/{batch_id}")).json()["batch_number"]

    resp = await client.get(
        f"/vault/v1/business/batch/{batch_number}/versions", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200, resp.text
    versions = resp.json()
    assert len(versions) == 1
    obj = versions[0]
    assert obj["object_type"] == "batch"
    assert obj["internal_version"] == 1
    assert obj["status"] == "released"
    assert obj["canonical_payload"]["decision"] == "released"
    assert obj["canonical_payload"]["batch_number"] == batch_number
    assert len(obj["canonical_payload"]["steps"]) == 2

    integrity = (
        await client.get(f"/vault/v1/objects/{obj['object_id']}/integrity", headers=auth_headers(admin_token))
    ).json()
    assert integrity == {"object_id": obj["object_id"], "digest_valid": True, "link_valid": True}


async def test_second_release_increments_version_and_supersedes(db, seeded):
    first = await vault_service.release_master(
        db, object_type="widget", business_id="W-1", canonical_payload={"n": 1}
    )
    await db.commit()
    second = await vault_service.release_master(
        db, object_type="widget", business_id="W-1", canonical_payload={"n": 2}
    )
    await db.commit()

    assert first.internal_version == 1
    assert second.internal_version == 2
    assert second.supersedes_object_id == first.object_id

    versions = await vault_service.list_versions_for_business_id(db, object_type="widget", business_id="W-1")
    assert [v.internal_version for v in versions] == [1, 2]


async def test_concurrent_release_same_business_id_raises_clean_conflict(seeded):
    """Two genuinely concurrent sessions both read `latest=None` before either commits, so both compute
    internal_version=1 -- the DB's UNIQUE(object_type, business_id, internal_version) constraint (migration
    616aed1058e9) is what actually stops the second one from silently overwriting the first; this proves
    release_master() converts that into a clean ConcurrentVaultReleaseError rather than a raw asyncpg error.
    """
    import asyncio

    from app.core.db import SessionLocal
    from app.mutation.errors import ConcurrentVaultReleaseError

    async def _release_and_commit(payload):
        async with SessionLocal() as session:
            obj = await vault_service.release_master(
                session, object_type="widget", business_id="W-RACE", canonical_payload=payload
            )
            await session.commit()
            return obj

    results = await asyncio.gather(
        _release_and_commit({"n": 1}), _release_and_commit({"n": 2}), return_exceptions=True
    )
    successes = [r for r in results if not isinstance(r, Exception)]
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(successes) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], ConcurrentVaultReleaseError)


async def test_verify_integrity_detects_tampering(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.vault")

    async with db.begin():
        obj = await vault_service.release_master(
            db, object_type="widget", business_id="W-TAMPER", canonical_payload={"n": 1}
        )
        object_id = obj.object_id

    migration_engine = create_async_engine(settings.migration_database_url)
    try:
        async with migration_engine.begin() as conn:
            await conn.execute(
                VaultObject.__table__.update()
                .where(VaultObject.object_id == object_id)
                .values(canonical_payload={"n": 999})
            )
    finally:
        await migration_engine.dispose()

    resp = await client.get(f"/vault/v1/objects/{object_id}/integrity", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["digest_valid"] is False


async def test_generic_release_requires_an_independent_qa_releaser_signature(client, seeded, db):
    """SG-035 (2026-09-10, project-owner-directed, "follow the ebmr-edhr docs"): Document 106 section 9
    row 2 -- the generic vault master release is `Released` by a "QA Approver / Batch Release" ->
    "QA Releaser". The required role is enforced; this endpoint has no prior record, so the "independent
    of every production performer" clause has no data source here (documented)."""
    from app.core.security import hash_password
    from app.modules.iam.models import User, UserSiteRole
    from app.modules.signature.models import SignaturePolicy

    async with db.begin():
        await _make_admin(db, seeded)
        signer = User(
            username="qa.vault", email="qa.vault@example.com", full_name="QA Releaser",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(signer)
        await db.flush()
        db.add(UserSiteRole(user_id=signer.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        db.add(SignaturePolicy(
            record_type="vault_object", action="release", meaning="Released",
            required_role_id=seeded["roles"]["QA Releaser"].id, requires_independent_signer=True,
            signature_required=True, reason_required=True,
        ))
    admin_token = await login(client, "admin.vault")
    signer_token = await login(client, "qa.vault")
    body = {"idempotency_key": idem(), "object_type": "widget", "business_id": "W-DIRECT", "canonical_payload": {"n": 1}}

    # Admin holds no "QA Releaser" role -> the signature-policy role check rejects it.
    resp = await client.post("/vault/v1/masters/widget/W-DIRECT/release", json={**body, "idempotency_key": idem()},
                             headers=auth_headers(admin_token))
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"

    # QA Releaser, no challenge -> MISSING_SIGNATURE.
    resp = await client.post("/vault/v1/masters/widget/W-DIRECT/release", json={**body, "idempotency_key": idem()},
                             headers=auth_headers(signer_token))
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"

    # QA Releaser + a valid challenge bound to the canonical payload -> released.
    challenge = (
        await client.post(
            "/vault/v1/masters/widget/W-DIRECT/signature-challenges",
            json={"action": "release", "canonical_payload": {"n": 1}}, headers=auth_headers(signer_token),
        )
    ).json()
    assert challenge["meaning"] == "Released"
    resp = await client.post(
        "/vault/v1/masters/widget/W-DIRECT/release",
        json={**body, "idempotency_key": idem(), "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD},
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


async def test_correction_request_then_complete_fails_closed(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.vault")

    async with db.begin():
        obj = await vault_service.release_master(
            db, object_type="widget", business_id="W-CORRECT", canonical_payload={"n": 1}
        )
        object_id = obj.object_id

    resp = await client.post(
        f"/vault/v1/objects/{object_id}/corrections",
        json={
            "idempotency_key": idem(),
            "record_object_id": str(object_id),
            "reason_code": "DATA_ENTRY_ERROR",
            "reason_text": "Quantity was mistyped.",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    correction_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/vault/v1/corrections/{correction_id}/complete",
        json={
            "idempotency_key": idem(),
            "correction_id": correction_id,
            "corrected_canonical_payload": {"n": 2},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_unauthorized_without_token_rejected(client):
    resp = await client.get("/vault/v1/business/batch/anything/versions")
    assert resp.status_code == 401


async def test_operator_without_vault_permission_forbidden(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.get("/vault/v1/business/batch/anything/versions", headers=auth_headers(op_token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"
