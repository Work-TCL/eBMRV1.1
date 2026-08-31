"""WP-01 Document 07 (SPEC-IAM-001) policy engine — the data-driven replacement for hardcoded
require_role()/require_admin_anywhere() checks. Covers: a permission grant unlocking a previously
forbidden action, a Document 107 standing-role-pair SoD conflict denying an otherwise-permitted action,
and the /permissions + /roles/{id}/permissions + /policy/v1/decisions endpoints.
"""

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam.models import Permission, Role, SodRule, User, UserSiteRole
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _promote_to_admin(db, user_id, site_id):
    async with db.begin():
        admin_role = (await db.execute(select(Role).where(Role.name == "Admin"))).scalar_one()
        db.add(UserSiteRole(user_id=user_id, site_id=site_id, role_id=admin_role.id))


async def _create_role_and_user(db, site_id, role_name, username):
    async with db.begin():
        role = Role(name=role_name)
        db.add(role)
        await db.flush()
        user = User(
            username=username,
            email=f"{username}@example.com",
            full_name=username,
            password_hash=hash_password(DEMO_PASSWORD),
            status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=site_id, role_id=role.id))
    return role, user


async def _create_product_recipe_batch(client, token, site_id, batch_number):
    resp = await client.post(
        "/products",
        json={"idempotency_key": idem(), "site_id": str(site_id), "code": f"P-{batch_number}", "name": "P"},
        headers=auth_headers(token),
    )
    product_id = resp.json()["aggregate_id"]
    resp = await client.post(
        "/recipes",
        json={
            "idempotency_key": idem(),
            "product_id": product_id,
            "version": 1,
            "steps": [{"step_number": 1, "name": "Step 1", "requires_signature": False}],
        },
        headers=auth_headers(token),
    )
    recipe_id = resp.json()["aggregate_id"]
    resp = await client.post(
        "/batches",
        json={
            "idempotency_key": idem(),
            "site_id": str(site_id),
            "product_id": product_id,
            "recipe_id": recipe_id,
            "recipe_version": 1,
            "batch_number": batch_number,
            "target_quantity": "1.000000",
            "uom": "kg",
        },
        headers=auth_headers(token),
    )
    batch_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/batches/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/batches/{batch_id}")).json()
    return batch_id, detail["steps"][0]


async def test_permission_grant_unlocks_previously_forbidden_action(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    _role, _user = await _create_role_and_user(db, site_id, "Line Lead", "linelead1")
    ll_token = await login(client, "linelead1")

    batch_id, step1 = await _create_product_recipe_batch(client, admin_token, site_id, "B-POLICY-1")

    # Line Lead holds no permission yet -> denied.
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 2,
            "batch_step_id": step1["batch_step_id"],
        },
        headers=auth_headers(ll_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"

    # Grant Line Lead the batch_step.start permission.
    role_id = str(_role.id)
    permission_id = (
        await db.execute(select(Permission.id).where(Permission.code == "batch_step.start"))
    ).scalar_one()
    resp = await client.post(
        f"/roles/{role_id}/permissions",
        json={"idempotency_key": idem(), "role_id": role_id, "permission_ids": [str(permission_id)]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/roles/{role_id}/permissions", headers=auth_headers(admin_token))
    assert [p["code"] for p in resp.json()] == ["batch_step.start"]

    # Same action now succeeds.
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 2,
            "batch_step_id": step1["batch_step_id"],
        },
        headers=auth_headers(ll_token),
    )
    assert resp.status_code == 200, resp.text


async def test_sod_conflict_denies_gated_action_even_with_permission(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    role_a, user = await _create_role_and_user(db, site_id, "Conflict Role A", "conflicted1")
    async with db.begin():
        role_b = Role(name="Conflict Role B")
        db.add(role_b)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=site_id, role_id=role_b.id))

        permission = (
            await db.execute(select(Permission).where(Permission.code == "batch_step.start"))
        ).scalar_one()
        from app.modules.iam.models import RolePermission

        db.add(RolePermission(role_id=role_a.id, permission_id=permission.id))

        db.add(
            SodRule(
                code="TEST-SOD-001",
                rule_type="STANDING_ROLE_PAIR",
                role_a="Conflict Role A",
                role_b="Conflict Role B",
                severity="PROHIBITED",
                rationale="Test-only conflict rule.",
                source_reference="test",
            )
        )

    conflicted_token = await login(client, "conflicted1")
    batch_id, step1 = await _create_product_recipe_batch(client, admin_token, site_id, "B-POLICY-2")

    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 2,
            "batch_step_id": step1["batch_step_id"],
        },
        headers=auth_headers(conflicted_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SOD_CONFLICT"


async def test_list_permissions_includes_seeded_catalog(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.get("/permissions", headers=auth_headers(op_token))
    assert resp.status_code == 200, resp.text
    codes = {p["code"] for p in resp.json()}
    assert {"batch_step.start", "batch.review", "batch.release", "material_lot.disposition", "platform.administer"} <= codes


async def test_policy_decision_endpoint_reports_allow_and_deny(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    resp = await client.post(
        "/policy/v1/decisions",
        json={"action": "batch_step.start", "site_id": str(site_id)},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["decision"] == "ALLOW"
    assert "Operator" in body["held_roles"]

    resp = await client.post(
        "/policy/v1/decisions",
        json={"action": "batch.release", "site_id": str(site_id)},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["decision"] == "DENY"
    assert body["reason"] == "ROLE_MISSING"
