"""Document 12 (SPEC-EBMR-003) -- the buildable slice: create a device lot, bulk-create serial units
under it, hold a unit, and the read paths (by-serial, history, release-readiness). New module -- no
legacy device/DHR stub existed to leave untouched, so there's nothing to prove "unmodified" here; the
full pre-existing suite (batch/batch_execution/etc.) still passes unmodified regardless. Everything
gated on device_component_usage/device_test_result/device_defect/device_evidence_inheritance or on
absent infrastructure (Equipment master, NCR/QMS, sterilization, packaging/labeling, DDCP profiles) is
out of scope this pass -- SG-049/SG-050.
"""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.device"):
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


async def _released_product_version(client, admin_token, site_id, tag):
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(),
            "product_business_id": f"DEVPRD-{tag}",
            "product_code": f"DEVPRD-{tag}",
            "name": "Device Test Product",
            "version_no": 1,
            "site_id": str(site_id),
            "manufacturing_profile_code": "device",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    product_version_id = resp.json()["aggregate_id"]
    await client.post(
        f"/products/v1/drafts/{product_version_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return product_version_id


async def _admin_and_released_product(db, client, seeded, tag):
    async with db.begin():
        await _make_admin(db, seeded, f"admin.device{tag}")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, f"admin.device{tag}")
    product_version_id = await _released_product_version(client, admin_token, seeded["site_id"], tag)
    return admin_token, product_version_id


def _lot_body(site_id, product_version_id, **overrides):
    body = {
        "idempotency_key": idem(),
        "site_id": str(site_id),
        "product_version_id": product_version_id,
        "udi_di": "00012345678905",
    }
    body.update(overrides)
    return body


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/devices/v1/lots", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_lot_requires_permission(client, seeded, db):
    admin_token, product_version_id = await _admin_and_released_product(db, client, seeded, "1")
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/devices/v1/lots",
        json=_lot_body(seeded["site_id"], product_version_id),
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_create_lot_rejects_draft_product(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.device2")
    admin_token = await login(client, "admin.device2")
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": "DEVPRD-2", "product_code": "DEVPRD-2",
            "name": "P", "version_no": 1, "site_id": str(seeded["site_id"]), "manufacturing_profile_code": "device",
        },
        headers=auth_headers(admin_token),
    )
    product_version_id = resp.json()["aggregate_id"]  # stays draft -- never submitted/released

    resp = await client.post(
        "/devices/v1/lots",
        json=_lot_body(seeded["site_id"], product_version_id),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_bulk_create_units_under_lot_and_read_by_serial(client, seeded, db):
    admin_token, product_version_id = await _admin_and_released_product(db, client, seeded, "3")
    resp = await client.post(
        "/devices/v1/lots",
        json=_lot_body(seeded["site_id"], product_version_id),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    lot_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/devices/v1/units/bulk-create",
        json={
            "idempotency_key": idem(),
            "device_lot_id": lot_id,
            "units": [{"serial_number": "SN-0001"}, {"serial_number": "SN-0002"}],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    receipts = resp.json()
    assert len(receipts) == 2

    detail = (
        await client.get(
            f"/devices/v1/units/by-serial/SN-0001", params={"site_id": str(seeded["site_id"])}, headers=auth_headers(admin_token)
        )
    ).json()
    assert detail["serial_number"] == "SN-0001"
    assert detail["device_lot_id"] == lot_id
    assert detail["udi_di"] == "00012345678905"
    assert detail["state"] == "created"


async def test_bulk_create_rejects_duplicate_serial_within_request(client, seeded, db):
    admin_token, product_version_id = await _admin_and_released_product(db, client, seeded, "4")
    resp = await client.post(
        "/devices/v1/lots", json=_lot_body(seeded["site_id"], product_version_id), headers=auth_headers(admin_token)
    )
    lot_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/devices/v1/units/bulk-create",
        json={"idempotency_key": idem(), "device_lot_id": lot_id, "units": [{"serial_number": "SN-DUP"}, {"serial_number": "SN-DUP"}]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text


async def test_bulk_create_rejects_existing_serial_at_site(client, seeded, db):
    admin_token, product_version_id = await _admin_and_released_product(db, client, seeded, "5")
    resp = await client.post(
        "/devices/v1/lots", json=_lot_body(seeded["site_id"], product_version_id), headers=auth_headers(admin_token)
    )
    lot_id = resp.json()["aggregate_id"]
    await client.post(
        "/devices/v1/units/bulk-create",
        json={"idempotency_key": idem(), "device_lot_id": lot_id, "units": [{"serial_number": "SN-EXIST"}]},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        "/devices/v1/units/bulk-create",
        json={"idempotency_key": idem(), "device_lot_id": lot_id, "units": [{"serial_number": "SN-EXIST"}]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert "SN-EXIST" in str(resp.json()["details"])


async def test_hold_unit_and_illegal_transition(client, seeded, db):
    admin_token, product_version_id = await _admin_and_released_product(db, client, seeded, "6")
    resp = await client.post(
        "/devices/v1/lots", json=_lot_body(seeded["site_id"], product_version_id), headers=auth_headers(admin_token)
    )
    lot_id = resp.json()["aggregate_id"]
    resp = await client.post(
        "/devices/v1/units/bulk-create",
        json={"idempotency_key": idem(), "device_lot_id": lot_id, "units": [{"serial_number": "SN-HOLD"}]},
        headers=auth_headers(admin_token),
    )
    unit_id = resp.json()[0]["aggregate_id"]

    resp = await client.post(
        f"/devices/v1/units/{unit_id}/hold",
        json={"idempotency_key": idem(), "unit_id": unit_id, "expected_version": 1, "reason": "suspected mislabel"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (
        await client.get(f"/devices/v1/units/{unit_id}/history", headers=auth_headers(admin_token))
    ).json()
    assert detail["state"] == "hold"

    resp = await client.post(
        f"/devices/v1/units/{unit_id}/hold",
        json={"idempotency_key": idem(), "unit_id": unit_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_stale_version_rejected(client, seeded, db):
    admin_token, product_version_id = await _admin_and_released_product(db, client, seeded, "7")
    resp = await client.post(
        "/devices/v1/lots", json=_lot_body(seeded["site_id"], product_version_id), headers=auth_headers(admin_token)
    )
    lot_id = resp.json()["aggregate_id"]
    resp = await client.post(
        "/devices/v1/units/bulk-create",
        json={"idempotency_key": idem(), "device_lot_id": lot_id, "units": [{"serial_number": "SN-STALE"}]},
        headers=auth_headers(admin_token),
    )
    unit_id = resp.json()[0]["aggregate_id"]

    resp = await client.post(
        f"/devices/v1/units/{unit_id}/hold",
        json={"idempotency_key": idem(), "unit_id": unit_id, "expected_version": 99},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    admin_token, product_version_id = await _admin_and_released_product(db, client, seeded, "8")
    key = idem()
    body = _lot_body(seeded["site_id"], product_version_id, idempotency_key=key)
    resp1 = await client.post("/devices/v1/lots", json=body, headers=auth_headers(admin_token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/devices/v1/lots", json=body, headers=auth_headers(admin_token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_release_readiness_reflects_held_units(client, seeded, db):
    admin_token, product_version_id = await _admin_and_released_product(db, client, seeded, "9")
    resp = await client.post(
        "/devices/v1/lots", json=_lot_body(seeded["site_id"], product_version_id), headers=auth_headers(admin_token)
    )
    lot_id = resp.json()["aggregate_id"]
    resp = await client.post(
        "/devices/v1/units/bulk-create",
        json={"idempotency_key": idem(), "device_lot_id": lot_id, "units": [{"serial_number": "SN-A"}, {"serial_number": "SN-B"}]},
        headers=auth_headers(admin_token),
    )
    unit_a_id = resp.json()[0]["aggregate_id"]

    readiness = (
        await client.get(f"/devices/v1/lots/{lot_id}/release-readiness", headers=auth_headers(admin_token))
    ).json()
    assert readiness["eligible"] is True
    assert readiness["unit_count"] == 2

    await client.post(
        f"/devices/v1/units/{unit_a_id}/hold",
        json={"idempotency_key": idem(), "unit_id": unit_a_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    readiness = (
        await client.get(f"/devices/v1/lots/{lot_id}/release-readiness", headers=auth_headers(admin_token))
    ).json()
    assert readiness["eligible"] is False
    assert readiness["blocked_unit_ids"] == [unit_a_id]
