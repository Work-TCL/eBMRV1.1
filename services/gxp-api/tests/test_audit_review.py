"""Document 05 (SPEC-GXP-003) — the audit review/search/export API layer. Covers the requirements
achievable against the existing `audit_events` schema (see docs/generated/18_SPEC_GAPS.md SG-029 for what
isn't): record/batch/user lookup, search filters, changed-field derivation, site-scoped visibility,
tamper detection via hash-chain recomputation, and the export command's real (currently fail-closed)
behavior — never a fabricated pass for the export happy path.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import Organization, Site, User, UserSiteRole
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.test"):
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


async def test_record_lookup_shows_changed_fields(client, seeded, db):
    async with db.begin():
        admin = await _make_admin(db, seeded)
    admin_token = await login(client, "admin.test")

    org = (await client.get("/organization", headers=auth_headers(admin_token))).json()
    resp = await client.patch(
        "/organization",
        json={"idempotency_key": idem(), "name": "Renamed Co."},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(
        f"/audit/v1/records/organization/{org['id']}", headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    event = body["items"][0]
    assert event["action"] == "Changed"
    assert event["changed_fields"] == ["name"]
    assert event["old_value"] == {"name": "Test Org"}
    assert event["new_value"] == {"name": "Renamed Co."}
    assert event["actor_username"] == "admin.test"


async def test_search_filters_by_action_and_actor(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.test")

    await client.patch(
        "/organization",
        json={"idempotency_key": idem(), "name": "Second Name"},
        headers=auth_headers(admin_token),
    )

    resp = await client.get(
        "/audit/v1/search",
        params={"aggregate_type": "organization", "action": "Changed"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] >= 1
    assert all(item["action"] == "Changed" for item in body["items"])

    admin_user = (await db.execute(select(User).where(User.username == "admin.test"))).scalar_one()
    resp = await client.get(
        "/audit/v1/search", params={"actor_id": str(admin_user.id)}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200, resp.text
    assert all(item["actor_id"] == str(admin_user.id) for item in resp.json()["items"])


async def test_unauthorized_without_token_rejected(client):
    resp = await client.get("/audit/v1/search")
    assert resp.status_code == 401


async def test_operator_without_audit_permission_forbidden(client, seeded):
    """The seeded Operator role is not granted audit.review — proves the permission gate is real, not
    just "any authenticated user"."""
    op_token = await login(client, "operator1")
    resp = await client.get("/audit/v1/search", headers=auth_headers(op_token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_cross_site_search_denied(client, seeded, db):
    """An actor with audit.review only at a second site cannot search events scoped to the seeded site,
    even though they hold the right action permission — site scoping is enforced independently of the
    action grant (REMEDIATION_R1 Fix 2's tenancy reasoning, applied here for the first time to a
    cross-cutting read endpoint)."""
    async with db.begin():
        org2 = (await db.execute(select(Organization).limit(1))).scalar_one()
        site2 = Site(organization_id=org2.id, code="T2", name="Second Site")
        db.add(site2)
        await db.flush()
        user = User(
            username="reviewer.site2",
            email="reviewer.site2@example.com",
            full_name="Reviewer Site 2",
            password_hash=hash_password(DEMO_PASSWORD),
            status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=site2.id, role_id=seeded["roles"]["QA Reviewer"].id))

    token = await login(client, "reviewer.site2")
    resp = await client.get(
        "/audit/v1/search", params={"site_id": str(seeded["site_id"])}, headers=auth_headers(token)
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "FORBIDDEN"


async def test_verify_chain_detects_tampering(client, seeded, db):
    """Uses a batch aggregate rather than organization/site/role — those IAM aggregates have no version
    column and hardcode aggregate_version=1 on every event, so their "previous event" lookup order is
    ambiguous once more than one event exists (a pre-existing quirk in the IAM commands built before this
    pass, out of scope to fix here). Batch has a real incrementing version, giving a deterministic chain.
    """
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.test")
    op_token = await login(client, "operator1")

    product_id = (
        await client.post(
            "/products",
            json={"idempotency_key": idem(), "site_id": str(seeded["site_id"]), "code": "P-AUD", "name": "P"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    recipe_id = (
        await client.post(
            "/recipes",
            json={
                "idempotency_key": idem(),
                "product_id": product_id,
                "version": 1,
                "steps": [{"step_number": 1, "name": "Step 1", "requires_signature": False}],
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    batch_id = (
        await client.post(
            "/batches",
            json={
                "idempotency_key": idem(),
                "site_id": str(seeded["site_id"]),
                "product_id": product_id,
                "recipe_id": recipe_id,
                "recipe_version": 1,
                "batch_number": "B-AUD",
                "target_quantity": "10.000000",
                "uom": "kg",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    resp = await client.post(
        f"/batches/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    # Tamper with the v1 (Created) event directly — the app role has no UPDATE grant on audit_events at
    # all (migration 0002_append_only_privilege_lockdown), so this goes through the migration role, same
    # technique as REMEDIATION_R1's signature-policy-deletion test.
    events = (
        await db.execute(
            select(AuditEvent)
            .where(AuditEvent.aggregate_type == "batch", AuditEvent.aggregate_id == uuid.UUID(batch_id))
            .order_by(AuditEvent.aggregate_version)
        )
    ).scalars().all()
    assert len(events) == 2  # Created (v1), Issued (v2)
    tampered_id = events[0].id

    migration_engine = create_async_engine(settings.migration_database_url)
    try:
        async with migration_engine.begin() as conn:
            await conn.execute(
                AuditEvent.__table__.update()
                .where(AuditEvent.id == tampered_id)
                .values(new_value={"batch_number": "TAMPERED"})
            )
    finally:
        await migration_engine.dispose()

    resp = await client.get(
        f"/audit/v1/batches/{batch_id}",
        params={"verify_chain": "true"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    by_id = {item["id"]: item for item in resp.json()["items"]}
    assert by_id[str(tampered_id)]["chain_valid"] is False
    untampered = [item for item in resp.json()["items"] if item["id"] != str(tampered_id)]
    assert untampered and all(item["chain_valid"] is True for item in untampered)


async def test_export_fails_closed_pending_signature_policy(client, seeded, db):
    """No policy row exists for record_type=audit_export (Document 106's approved floor doesn't cover
    this action — see SG-029) — this asserts the real, current behavior rather than a fabricated pass."""
    async with db.begin():
        await _make_admin(db, seeded)
    admin_token = await login(client, "admin.test")

    resp = await client.post(
        "/audit/v1/exports",
        json={"idempotency_key": idem(), "filter": {"aggregate_type": "organization"}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_export_requires_export_permission_not_just_review(client, seeded):
    """QA Reviewer holds audit.review (can search) but not audit.export (cannot request an export) —
    proves the two permissions are independently enforced, not one implying the other."""
    reviewer_token = await login(client, "qa.reviewer")
    resp = await client.post(
        "/audit/v1/exports",
        json={"idempotency_key": idem(), "filter": {"aggregate_type": "organization"}},
        headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"
