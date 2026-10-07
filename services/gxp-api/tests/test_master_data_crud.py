"""Edit + guarded delete for master/reference data (Site, Material) — REMEDIATION follow-on.
Delete must be blocked with a clear reason whenever another table still references the row.

Product/Recipe's own edit+guarded-delete tests (`test_product_edit_and_delete_guard`,
`test_recipe_edit_and_delete_locked_once_batch_uses_it`) are removed, not ported (SG-044/SG-149/SG-173
Phase 4/5, ADR-0013, 2026-09-23): they exercised the retired `app.modules.{product,recipe}`'s free-form
PATCH/DELETE, a mutability model the authoritative `product_master`/`recipe_master` modules deliberately
do not offer at all -- those modules use an immutable draft->submit->release->supersede version lifecycle
(no PATCH, no DELETE on any version, released or not), the same "no true delete for a versioned regulated
master" precedent already established for `aseptic_profile_version` (SG-176). There is no equivalent
behavior to port; the capability itself was superseded, not merely relocated.

`test_site_create_edit_and_delete_guard` is kept and ported: it only needs *some* site-referencing row to
prove the delete guard fires, and now creates a `product_master.ProductVersion` directly via the ORM
instead of going through the retired `/products` endpoint -- the guard itself
(`find_all_blocking_references`, schema-driven across all `iam.sites` FK columns) was already unaffected
by the retirement.
"""

import uuid

from sqlalchemy import select

from app.modules.iam.models import Role, UserSiteRole
from app.modules.product_master.models import ProductVersion
from tests.conftest import auth_headers, idem, login


async def _promote_to_admin(db, user_id, site_id):
    async with db.begin():
        admin_role = (await db.execute(select(Role).where(Role.name == "Admin"))).scalar_one()
        db.add(UserSiteRole(user_id=user_id, site_id=site_id, role_id=admin_role.id))


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

    # A product_master version at this site blocks deletion (find_all_blocking_references is
    # schema-driven across all iam.sites FK columns, not specific to any one module -- any referencing
    # row proves the guard).
    async with db.begin():
        db.add(ProductVersion(
            product_business_id="P-CRUD", version_no=1, product_code="P-CRUD", name="CRUD Product",
            site_id=uuid.UUID(site_id), manufacturing_profile_code="pharma",
        ))
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


async def test_material_edit_and_delete_guard(client, seeded, db):
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    material_id = await _create_material(client, admin_token, seeded["site_id"], code="M-DEL")

    resp = await client.patch(
        f"/materials/{material_id}",
        json={
            "idempotency_key": idem(), "material_id": material_id, "expected_version": 1,
            "name": "Renamed Material", "status": "active",
        },
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


async def test_material_update_rejects_stale_expected_version(client, seeded, db):
    # Bug fix: update_material() previously had no optimistic-concurrency check at all -- two concurrent
    # edits would silently overwrite each other with no conflict signal. Mirrors the same
    # StaleVersionError/409 shape every other material command already uses (examine_receipt,
    # release_material_lot, etc.).
    await _promote_to_admin(db, seeded["users"]["operator1"].id, seeded["site_id"])
    admin_token = await login(client, "operator1")
    material_id = await _create_material(client, admin_token, seeded["site_id"], code="M-STALE")

    # A real edit succeeds and advances the version to 2.
    resp = await client.patch(
        f"/materials/{material_id}",
        json={
            "idempotency_key": idem(), "material_id": material_id, "expected_version": 1,
            "name": "First rename", "status": "active",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    # A second edit against the now-stale version 1 is rejected, not silently applied.
    resp = await client.patch(
        f"/materials/{material_id}",
        json={
            "idempotency_key": idem(), "material_id": material_id, "expected_version": 1,
            "name": "Second rename (stale)", "status": "active",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"

    # The record still reflects only the first, successful edit.
    resp = await client.get("/materials", params={"q": "M-STALE"}, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    row = resp.json()["items"][0]
    assert row["name"] == "First rename"
    assert row["version"] == 2
