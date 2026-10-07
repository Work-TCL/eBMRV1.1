"""Document 20 (SPEC-MAT-002B) warehouse_location update/retire — SG-081 (2026-09-22, project-owner-
directed): the entity had create (2026-09-07) but no update or delete/retire operation. Update covers
location_code/zone_type/environment_profile_id (rename); retire is a soft status change, since
MaterialLot.storage_location_id (req #4) can reference a location and a hard delete would orphan it."""

import uuid

from tests.conftest import auth_headers, idem, login


async def _create_location(client, token, site_id, warehouse_code="WH-NEW", location_code=None, zone_type="quarantine"):
    resp = await client.post(
        "/inventory/v1/warehouse-locations",
        json={
            "idempotency_key": idem(), "site_id": str(site_id), "warehouse_code": warehouse_code,
            "location_code": location_code or f"LOC-{uuid.uuid4().hex[:8]}", "zone_type": zone_type,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_create_warehouse_location_reports_version_and_site_id(client, seeded):
    token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    location_id = await _create_location(client, token, site_id)

    rows = (
        await client.get(f"/inventory/v1/warehouse-locations?site_id={site_id}", headers=auth_headers(token))
    ).json()["items"]
    created = next(r for r in rows if r["id"] == location_id)
    assert created["version"] == 1
    assert created["site_id"] == str(site_id)
    assert created["status"] == "active"


async def test_update_renames_location_code_and_zone_type(client, seeded):
    token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    location_id = await _create_location(client, token, site_id, location_code="LOC-RENAME-OLD")

    resp = await client.patch(
        f"/inventory/v1/warehouse-locations/{location_id}",
        json={
            "idempotency_key": idem(), "warehouse_location_id": location_id, "expected_version": 1,
            "location_code": "LOC-RENAME-NEW", "zone_type": "released",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resulting_version"] == 2

    rows = (
        await client.get(f"/inventory/v1/warehouse-locations?site_id={site_id}", headers=auth_headers(token))
    ).json()["items"]
    updated = next(r for r in rows if r["id"] == location_id)
    assert updated["location_code"] == "LOC-RENAME-NEW"
    assert updated["zone_type"] == "released"
    assert updated["version"] == 2


async def test_update_rejects_duplicate_location_code_at_same_site(client, seeded):
    token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    await _create_location(client, token, site_id, warehouse_code="WH-DUP", location_code="LOC-DUP-A")
    location_b = await _create_location(client, token, site_id, warehouse_code="WH-DUP", location_code="LOC-DUP-B")

    resp = await client.patch(
        f"/inventory/v1/warehouse-locations/{location_b}",
        json={
            "idempotency_key": idem(), "warehouse_location_id": location_b, "expected_version": 1,
            "location_code": "LOC-DUP-A",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_update_rejects_stale_version(client, seeded):
    token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    location_id = await _create_location(client, token, site_id)

    resp = await client.patch(
        f"/inventory/v1/warehouse-locations/{location_id}",
        json={
            "idempotency_key": idem(), "warehouse_location_id": location_id, "expected_version": 99,
            "location_code": "LOC-WONT-APPLY",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_update_requires_warehouse_location_update_permission(client, seeded):
    op_token = await login(client, "operator1")
    admin_token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    location_id = await _create_location(client, admin_token, site_id)

    resp = await client.patch(
        f"/inventory/v1/warehouse-locations/{location_id}",
        json={
            "idempotency_key": idem(), "warehouse_location_id": location_id, "expected_version": 1,
            "location_code": "LOC-NOT-ALLOWED",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_retire_hides_location_from_the_active_list(client, seeded):
    token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    location_id = await _create_location(client, token, site_id, location_code="LOC-RETIRE-ME")

    resp = await client.post(
        f"/inventory/v1/warehouse-locations/{location_id}/retire",
        json={"idempotency_key": idem(), "warehouse_location_id": location_id, "expected_version": 1, "reason": "zone decommissioned"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["resulting_version"] == 2

    rows = (
        await client.get(f"/inventory/v1/warehouse-locations?site_id={site_id}", headers=auth_headers(token))
    ).json()["items"]
    assert not any(r["id"] == location_id for r in rows)


async def test_retire_requires_a_reason(client, seeded):
    token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    location_id = await _create_location(client, token, site_id)

    resp = await client.post(
        f"/inventory/v1/warehouse-locations/{location_id}/retire",
        json={"idempotency_key": idem(), "warehouse_location_id": location_id, "expected_version": 1, "reason": "  "},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_retire_blocked_while_material_is_stored_in_the_location(client, seeded, db):
    """A location referenced by MaterialLot.storage_location_id (req #4) cannot be retired out from
    under the material it currently holds."""
    from app.modules.iam.models import User
    from app.modules.material.models import Material, MaterialLot

    token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    location_id = await _create_location(client, token, site_id, location_code="LOC-OCCUPIED")

    async with db.begin():
        admin_user = (await db.execute(__import__("sqlalchemy").select(User).where(User.username == "supervisor1"))).scalar_one()
        material = Material(site_id=site_id, code="RM-WHLOC", name="Warehouse Location Test Material", uom="kg", status="active")
        db.add(material)
        await db.flush()
        db.add(
            MaterialLot(
                material_id=material.id, site_id=site_id, internal_lot=f"LOT-WHLOC-{uuid.uuid4().hex[:6]}",
                received_quantity="10", available_quantity="10", uom="kg", status="quarantine",
                received_by_user_id=admin_user.id, storage_location_id=uuid.UUID(location_id),
            )
        )

    resp = await client.post(
        f"/inventory/v1/warehouse-locations/{location_id}/retire",
        json={"idempotency_key": idem(), "warehouse_location_id": location_id, "expected_version": 1, "reason": "attempt while occupied"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"
