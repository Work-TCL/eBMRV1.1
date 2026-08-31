"""Minimal IAM admin surface: create users, create roles, assign a role at a site. Gated by the policy
engine (evaluate_policy, action="platform.administer") — anywhere for creation, at the target site for
assignment."""

from sqlalchemy import select

from app.modules.iam.models import Role, UserSiteRole
from tests.conftest import auth_headers, idem, login


async def _promote_to_admin(db, user_id, site_id):
    async with db.begin():
        admin_role = (await db.execute(select(Role).where(Role.name == "Admin"))).scalar_one()
        db.add(UserSiteRole(user_id=user_id, site_id=site_id, role_id=admin_role.id))


async def test_create_user_requires_admin(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/users",
        json={
            "idempotency_key": idem(),
            "username": "newop",
            "email": "newop@example.com",
            "full_name": "New Operator",
            "password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_create_role_and_duplicate_name_rejected(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/roles",
        json={"idempotency_key": idem(), "name": "Line Lead", "description": "Shift line lead"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/roles",
        json={"idempotency_key": idem(), "name": "Line Lead", "description": "duplicate"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_create_user_assign_role_and_list_shows_it(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/users",
        json={
            "idempotency_key": idem(),
            "username": "newop2",
            "email": "newop2@example.com",
            "full_name": "New Operator Two",
            "password": "ChangeMe123!",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    new_user_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/users",
        json={
            "idempotency_key": idem(),
            "username": "newop2",
            "email": "different@example.com",
            "full_name": "Duplicate Username",
            "password": "ChangeMe123!",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"

    operator_role = (await db.execute(select(Role).where(Role.name == "Operator"))).scalar_one()
    resp = await client.post(
        f"/users/{new_user_id}/roles",
        json={
            "idempotency_key": idem(),
            "user_id": new_user_id,
            "site_id": str(seeded["site_id"]),
            "role_id": str(operator_role.id),
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/users", params={"q": "newop2"}, headers=auth_headers(admin_token))
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["username"] == "newop2"
    assert any("Operator" in r for r in items[0]["roles"])


async def test_role_edit_and_delete_blocked_then_succeeds(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/roles",
        json={"idempotency_key": idem(), "name": "Shift Lead", "description": "original"},
        headers=auth_headers(admin_token),
    )
    role_id = resp.json()["aggregate_id"]

    resp = await client.patch(
        f"/roles/{role_id}",
        json={"idempotency_key": idem(), "role_id": role_id, "name": "Shift Lead", "description": "updated"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/roles", params={"q": "Shift Lead"}, headers=auth_headers(admin_token))
    assert resp.json()["items"][0]["description"] == "updated"

    # Assign it to someone, then deletion must be blocked.
    resp = await client.post(
        f"/users/{seeded['users']['operator1'].id}/roles",
        json={
            "idempotency_key": idem(),
            "user_id": str(seeded["users"]["operator1"].id),
            "site_id": str(seeded["site_id"]),
            "role_id": role_id,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.request(
        "DELETE",
        f"/roles/{role_id}",
        json={"idempotency_key": idem(), "role_id": role_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"
    assert "referenced by" in resp.json()["message"]

    # A never-assigned role deletes cleanly.
    resp = await client.post(
        "/roles",
        json={"idempotency_key": idem(), "name": "Unused Role"},
        headers=auth_headers(admin_token),
    )
    unused_role_id = resp.json()["aggregate_id"]
    resp = await client.request(
        "DELETE",
        f"/roles/{unused_role_id}",
        json={"idempotency_key": idem(), "role_id": unused_role_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.get("/roles", params={"q": "Unused Role"}, headers=auth_headers(admin_token))
    assert resp.json()["total"] == 0


async def test_user_deactivate_blocks_login_then_reactivate_restores_it(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    qa_reviewer_id = seeded["users"]["qa.reviewer"].id

    resp = await client.post(
        f"/users/{qa_reviewer_id}/deactivate",
        json={"idempotency_key": idem(), "user_id": str(qa_reviewer_id)},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/auth/token", data={"username": "qa.reviewer", "password": "ChangeMe123!"}
    )
    assert resp.status_code == 401

    resp = await client.post(
        f"/users/{qa_reviewer_id}/reactivate",
        json={"idempotency_key": idem(), "user_id": str(qa_reviewer_id)},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    reviewer_token = await login(client, "qa.reviewer")
    assert reviewer_token


async def test_organization_edit_requires_admin_then_succeeds(client, seeded, db):
    op_token = await login(client, "operator1")
    resp = await client.patch(
        "/organization",
        json={"idempotency_key": idem(), "name": "Should Fail"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403

    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    resp = await client.patch(
        "/organization",
        json={"idempotency_key": idem(), "name": "Renamed Manufacturing Co."},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/organization", headers=auth_headers(admin_token))
    assert resp.json()["name"] == "Renamed Manufacturing Co."
