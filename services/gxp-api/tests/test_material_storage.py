"""Client requirement #4 -- Material Master is_in_house/default_storage_condition, and MaterialLot
storage_location_id/storage_condition captured at receive/examine time."""

from tests.conftest import auth_headers, idem, login
from tests.test_material_flow import _create_material, _receive_lot
from tests.test_material_receipt_flow import _create_receipt, _examine_clean


async def test_create_material_with_storage_defaults(client, seeded):
    pe_token = await login(client, "process.engineer")
    resp = await client.post(
        "/materials",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "code": "RM-STORAGE-1",
            "name": "Storage Test Material", "uom": "kg", "is_in_house": True,
            "default_storage_condition": "cold_storage",
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text

    listing = (await client.get("/materials")).json()
    item = next(i for i in listing["items"] if i["id"] == resp.json()["aggregate_id"])
    assert item["is_in_house"] is True
    assert item["default_storage_condition"] == "cold_storage"


async def test_create_material_rejects_invalid_storage_condition(client, seeded):
    pe_token = await login(client, "process.engineer")
    resp = await client.post(
        "/materials",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "code": "RM-STORAGE-2",
            "name": "Storage Test Material 2", "uom": "kg", "default_storage_condition": "on-the-moon",
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_update_material_storage_fields(client, seeded):
    material_id = await _create_material(client, seeded["site_id"], code="RM-STORAGE-3")
    pe_token = await login(client, "process.engineer")

    resp = await client.patch(
        f"/materials/{material_id}",
        json={
            "idempotency_key": idem(), "material_id": material_id, "name": "Storage Test Material 3",
            "status": "active", "is_in_house": True, "default_storage_condition": "freezer",
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text

    listing = (await client.get("/materials")).json()
    item = next(i for i in listing["items"] if i["id"] == material_id)
    assert item["is_in_house"] is True
    assert item["default_storage_condition"] == "freezer"


async def test_receive_lot_with_storage_location_and_condition(client, seeded):
    material_id = await _create_material(client, seeded["site_id"], code="RM-STORAGE-4")
    op_token = await login(client, "operator1")
    location_id = str(seeded["locations"]["QUARANTINE-01"].id)

    resp = await client.post(
        f"/materials/{material_id}/lots",
        json={
            "idempotency_key": idem(), "material_id": material_id, "site_id": str(seeded["site_id"]),
            "internal_lot": "LOT-STORAGE-4", "received_quantity": "50.000000", "uom": "kg",
            "storage_location_id": location_id, "storage_condition": "ambient",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    lot_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/material-lots/{lot_id}")).json()
    assert detail["storage_location_id"] == location_id
    assert detail["storage_condition"] == "ambient"


async def test_receive_lot_rejects_invalid_storage_condition(client, seeded):
    material_id = await _create_material(client, seeded["site_id"], code="RM-STORAGE-5")
    op_token = await login(client, "operator1")

    resp = await client.post(
        f"/materials/{material_id}/lots",
        json={
            "idempotency_key": idem(), "material_id": material_id, "site_id": str(seeded["site_id"]),
            "internal_lot": "LOT-STORAGE-5", "received_quantity": "50.000000", "uom": "kg",
            "storage_condition": "on-the-moon",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_receive_lot_rejects_unknown_storage_location(client, seeded):
    material_id = await _create_material(client, seeded["site_id"], code="RM-STORAGE-6")
    op_token = await login(client, "operator1")

    resp = await client.post(
        f"/materials/{material_id}/lots",
        json={
            "idempotency_key": idem(), "material_id": material_id, "site_id": str(seeded["site_id"]),
            "internal_lot": "LOT-STORAGE-6", "received_quantity": "50.000000", "uom": "kg",
            "storage_location_id": "00000000-0000-0000-0000-000000000000",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 404, resp.text


async def test_examine_receipt_sets_lot_storage_fields(client, seeded):
    material_id = await _create_material(client, seeded["site_id"], code="RM-STORAGE-7")
    op_token = await login(client, "operator1")
    receipt_id = await _create_receipt(client, op_token, seeded["site_id"], material_id, receipt_number="RCPT-STORAGE-7")
    location_id = str(seeded["locations"]["RELEASED-01"].id)

    resp = await client.post(
        f"/materials/v1/receipts/{receipt_id}/examine",
        json={
            "idempotency_key": idem(), "receipt_id": receipt_id, "expected_version": 1,
            "labeling_ok": True, "damage_observed": False, "seal_broken": False,
            "contamination_observed": False, "identity_confirmed": True, "internal_lot": "LOT-STORAGE-7",
            "container_count": 1, "storage_location_id": location_id, "storage_condition": "controlled_temperature",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    listing = (await client.get("/material-lots")).json()
    lot = next(i for i in listing["items"] if i["internal_lot"] == "LOT-STORAGE-7")
    assert lot["storage_location_id"] == location_id
    assert lot["storage_condition"] == "controlled_temperature"
