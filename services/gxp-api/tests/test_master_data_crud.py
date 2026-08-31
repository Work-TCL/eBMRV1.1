"""Edit + guarded delete for master/reference data (Site, Product, Material, Recipe) — REMEDIATION follow-on.
Delete must be blocked with a clear reason whenever another table still references the row; Recipe additionally
locks edit (not just delete) once a batch has used it, since a batch freezes its recipe as an execution
snapshot at issue time (BAT-FR-003) — editing it after the fact would silently change what that batch appears
to have run against.
"""

from sqlalchemy import select

from app.modules.iam.models import Role, UserSiteRole
from tests.conftest import auth_headers, idem, login


async def _promote_to_admin(db, user_id, site_id):
    async with db.begin():
        admin_role = (await db.execute(select(Role).where(Role.name == "Admin"))).scalar_one()
        db.add(UserSiteRole(user_id=user_id, site_id=site_id, role_id=admin_role.id))


async def _create_product(client, token, site_id, code="P-CRUD"):
    resp = await client.post(
        "/products",
        json={"idempotency_key": idem(), "site_id": str(site_id), "code": code, "name": "CRUD Product"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _create_recipe(client, token, product_id, version=1, signed=False):
    resp = await client.post(
        "/recipes",
        json={
            "idempotency_key": idem(),
            "product_id": product_id,
            "version": version,
            "steps": [{"step_number": 1, "name": "Step 1", "requires_signature": False}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _create_material(client, token, site_id, code="M-CRUD"):
    resp = await client.post(
        "/materials",
        json={"idempotency_key": idem(), "site_id": str(site_id), "code": code, "name": "CRUD Material", "uom": "kg"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_site_create_edit_and_delete_guard(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")

    resp = await client.post(
        "/sites", json={"idempotency_key": idem(), "code": "SITE2", "name": "Second Site"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200, resp.text
    site_id = resp.json()["aggregate_id"]

    resp = await client.patch(
        f"/sites/{site_id}",
        json={"idempotency_key": idem(), "site_id": site_id, "code": "SITE2", "name": "Second Site Renamed"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    # A product at this site blocks deletion.
    await _create_product(client, admin_token, site_id)
    resp = await client.request(
        "DELETE", f"/sites/{site_id}", json={"idempotency_key": idem(), "site_id": site_id}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 422
    assert "referenced by" in resp.json()["message"]

    # An empty site deletes cleanly.
    resp = await client.post(
        "/sites", json={"idempotency_key": idem(), "code": "SITE3", "name": "Empty Site"}, headers=auth_headers(admin_token)
    )
    empty_site_id = resp.json()["aggregate_id"]
    resp = await client.request(
        "DELETE",
        f"/sites/{empty_site_id}",
        json={"idempotency_key": idem(), "site_id": empty_site_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_site_create_requires_admin(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/sites", json={"idempotency_key": idem(), "code": "SITEX", "name": "X"}, headers=auth_headers(op_token)
    )
    assert resp.status_code == 403


async def test_product_edit_and_delete_guard(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    product_id = await _create_product(client, admin_token, seeded["site_id"], code="P-DEL")

    resp = await client.patch(
        f"/products/{product_id}",
        json={"idempotency_key": idem(), "product_id": product_id, "name": "Renamed Product", "status": "active"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    await _create_recipe(client, admin_token, product_id)
    resp = await client.request(
        "DELETE",
        f"/products/{product_id}",
        json={"idempotency_key": idem(), "product_id": product_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert "referenced by" in resp.json()["message"]

    unused_product_id = await _create_product(client, admin_token, seeded["site_id"], code="P-UNUSED")
    resp = await client.request(
        "DELETE",
        f"/products/{unused_product_id}",
        json={"idempotency_key": idem(), "product_id": unused_product_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_material_edit_and_delete_guard(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    material_id = await _create_material(client, admin_token, seeded["site_id"], code="M-DEL")

    resp = await client.patch(
        f"/materials/{material_id}",
        json={"idempotency_key": idem(), "material_id": material_id, "name": "Renamed Material", "status": "active"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/materials/{material_id}/lots",
        json={
            "idempotency_key": idem(),
            "material_id": material_id,
            "site_id": str(seeded["site_id"]),
            "internal_lot": "LOT-CRUD-1",
            "received_quantity": "10.000000",
            "uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.request(
        "DELETE",
        f"/materials/{material_id}",
        json={"idempotency_key": idem(), "material_id": material_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert "referenced by" in resp.json()["message"]

    unused_material_id = await _create_material(client, admin_token, seeded["site_id"], code="M-UNUSED")
    resp = await client.request(
        "DELETE",
        f"/materials/{unused_material_id}",
        json={"idempotency_key": idem(), "material_id": unused_material_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_recipe_edit_and_delete_locked_once_batch_uses_it(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    product_id = await _create_product(client, admin_token, seeded["site_id"], code="P-RECIPE")
    recipe_id = await _create_recipe(client, admin_token, product_id)

    resp = await client.patch(
        f"/recipes/{recipe_id}",
        json={
            "idempotency_key": idem(),
            "recipe_id": recipe_id,
            "steps": [{"step_number": 1, "name": "Renamed Step", "requires_signature": False}],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/batches",
        json={
            "idempotency_key": idem(),
            "site_id": str(seeded["site_id"]),
            "product_id": product_id,
            "recipe_id": recipe_id,
            "recipe_version": 1,
            "batch_number": "B-RECIPE-LOCK",
            "target_quantity": "1.000000",
            "uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.patch(
        f"/recipes/{recipe_id}",
        json={
            "idempotency_key": idem(),
            "recipe_id": recipe_id,
            "steps": [{"step_number": 1, "name": "Should Not Apply", "requires_signature": False}],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert "referenced by" in resp.json()["message"]

    resp = await client.request(
        "DELETE",
        f"/recipes/{recipe_id}",
        json={"idempotency_key": idem(), "recipe_id": recipe_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert "referenced by" in resp.json()["message"]

    unused_recipe_id = await _create_recipe(client, admin_token, product_id, version=2)
    resp = await client.request(
        "DELETE",
        f"/recipes/{unused_recipe_id}",
        json={"idempotency_key": idem(), "recipe_id": unused_recipe_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
