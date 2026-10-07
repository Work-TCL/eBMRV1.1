"""Document 20 (SPEC-MAT-002B) — Inventory, Lot/Container & Warehouse. Extends the Document 19 receipt/
examine/release flow with: put-away (transfer with no from_location, INV-FR-008), reservation + the one
signed operation (release, Document 106 row 46, INV-FR-010/011), transfer between locations (INV-FR-008),
container split/merge (INV-FR-023/024), cycle count (INV-FR-020/022), and the read-only availability/
ledger/reconciliation endpoints (INV-FR-003/029/028)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.modules.genealogy import service as genealogy_service
from app.modules.material.models import (
    InventoryAdjustmentRequest,
    InventoryReservation,
    InventoryTransaction,
    MaterialContainer,
    MaterialLot,
    WarehouseLocation,
)
from app.modules.supplier_quality.models import Supplier
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_material_receipt_flow import _create_receipt, _examine_clean
from tests.test_qms_scar import _create_supplier, _make_admin


async def _create_material(client, site_id, code="RM-D20", name="Raw Material D20", uom="kg"):
    # 2026-09-18: material.create is now Process Engineer/Admin-only (RBAC gap closure) -- always
    # authors as process.engineer regardless of which actor the calling test is otherwise exercising.
    pe_token = await login(client, "process.engineer")
    resp = await client.post(
        "/materials",
        json={"idempotency_key": idem(), "site_id": str(site_id), "code": code, "name": name, "uom": uom},
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _receive_and_examine(
    client, db, token, site_id, code, internal_lot, container_count=1, quantity="100.000000", expiry_date=None
):
    material_id = await _create_material(client, site_id, code=code, name=code)
    receipt_body = {
        "idempotency_key": idem(),
        "site_id": str(site_id),
        "receipt_number": f"RCPT-{internal_lot}",
        "material_id": material_id,
        "received_gross_quantity": quantity,
        "accepted_quantity": quantity,
        "uom": "kg",
    }
    if expiry_date is not None:
        receipt_body["expiry_date"] = expiry_date
    receipt_id = (
        await client.post("/materials/v1/receipts", json=receipt_body, headers=auth_headers(token))
    ).json()["aggregate_id"]
    resp = await client.post(
        f"/materials/v1/receipts/{receipt_id}/examine",
        json={
            "idempotency_key": idem(),
            "receipt_id": receipt_id,
            "expected_version": 1,
            "labeling_ok": True,
            "shipping_damage_observed": False,
            "container_damage_observed": False,
            "seal_broken": False,
            "identity_confirmed": True,
            "internal_lot": internal_lot,
            "container_count": container_count,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    lot = (
        await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == internal_lot))
    ).scalar_one()
    containers = (
        (await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot.id)))
        .scalars()
        .all()
    )
    return material_id, str(lot.id), [str(c.id) for c in containers]


async def _receive_lot_for_material(client, db, token, site_id, material_id, internal_lot, quantity="100.000000", expiry_date=None):
    """Like `_receive_and_examine` above, but against an *existing* material -- needed for the Client
    Topic 8 FEFO-override tests, where two lots of the same material are compared by expiry date."""
    receipt_body = {
        "idempotency_key": idem(),
        "site_id": str(site_id),
        "receipt_number": f"RCPT-{internal_lot}",
        "material_id": material_id,
        "received_gross_quantity": quantity,
        "accepted_quantity": quantity,
        "uom": "kg",
    }
    if expiry_date is not None:
        receipt_body["expiry_date"] = expiry_date
    receipt_id = (
        await client.post("/materials/v1/receipts", json=receipt_body, headers=auth_headers(token))
    ).json()["aggregate_id"]
    resp = await client.post(
        f"/materials/v1/receipts/{receipt_id}/examine",
        json={
            "idempotency_key": idem(),
            "receipt_id": receipt_id,
            "expected_version": 1,
            "labeling_ok": True,
            "shipping_damage_observed": False,
            "container_damage_observed": False,
            "seal_broken": False,
            "identity_confirmed": True,
            "internal_lot": internal_lot,
            "container_count": 1,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    lot = (await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == internal_lot))).scalar_one()
    container = (
        await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot.id))
    ).scalar_one()
    return str(lot.id), str(container.id)


async def _release_lot(client, token, lot_id, expected_version=1):
    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(token),
        )
    ).json()
    resp = await client.post(
        f"/materials/v1/lots/{lot_id}/release",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": expected_version,
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _put_away(client, token, lot_id, container_id, to_location_id, quantity):
    resp = await client.post(
        "/inventory/v1/transfers",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": container_id,
            "from_location_id": None,
            "to_location_id": to_location_id,
            "quantity": quantity,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _create_batch(client, token, site_id, code):
    """SG-173 / ADR-0013: the material / inventory / dispensing command layer reads batches from
    `ebmr.gxp_batch` (app.modules.batch_execution), and every `materials.*` table's `batch_id` FK now
    targets it (migration 0090). Build a minimal released Product Master / Recipe Master pair and the
    gxp_batch row directly — the material commands only read `batch.id` / `batch.site_id`.
    """
    import uuid as _uuid
    from decimal import Decimal as _Decimal

    from app.core.db import SessionLocal
    from app.modules.batch_execution.models import Batch as _GxpBatch
    from app.modules.product_master.models import ProductVersion as _ProductVersion
    from app.modules.recipe_master.models import RecipeFamily as _RecipeFamily, RecipeVersion as _RecipeVersion

    site_uuid = site_id if isinstance(site_id, _uuid.UUID) else _uuid.UUID(str(site_id))
    tag = f"{code}-{_uuid.uuid4().hex[:8]}"
    async with SessionLocal() as s:
        async with s.begin():
            pv = _ProductVersion(
                product_business_id=f"PB-{tag}", version_no=1, product_code=f"PC-{tag}", name=code,
                manufacturing_profile_code="pharma", lifecycle_state="released", site_id=site_uuid,
            )
            s.add(pv)
            await s.flush()
            rf = _RecipeFamily(
                product_business_id=pv.product_business_id, recipe_code=f"RC-{tag}", site_id=site_uuid,
                manufacturing_profile_code="pharma",
            )
            s.add(rf)
            await s.flush()
            rv = _RecipeVersion(
                recipe_family_id=rf.id, version_no=1, product_version_id=pv.id, site_id=site_uuid,
                lifecycle_state="released",
            )
            s.add(rv)
            await s.flush()
            batch = _GxpBatch(
                site_id=site_uuid, batch_number=f"B-{tag}", product_version_id=pv.id,
                recipe_version_id=rv.id, target_qty=_Decimal("10"), target_uom="kg",
                state="in_execution", version=1,
            )
            s.add(batch)
            await s.flush()
            return str(batch.id)


# --- INV-FR-008 put-away / transfer -----------------------------------------------------------------


async def test_put_away_creates_receipt_transaction_and_balance(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-PUTAWAY", "LOT-PUTAWAY"
    )
    await _release_lot(client, qa_token, lot_id)

    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")

    ledger = (await client.get(f"/inventory/v1/lots/{lot_id}/ledger", headers=auth_headers(qa_token))).json()
    assert ledger["items"][0]["transaction_type"] == "RECEIPT"
    assert ledger["items"][0]["quantity"] == "100.00000000"


async def test_put_away_wrong_zone_rejected(client, db, seeded):
    """INV-FR-008: still-quarantine lot cannot be put away into a released-status zone."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-WRONGZONE", "LOT-WRONGZONE"
    )

    resp = await client.post(
        "/inventory/v1/transfers",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": containers[0],
            "from_location_id": None,
            "to_location_id": released_location_id,
            "quantity": "100.000000",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_transfer_insufficient_on_hand_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    quarantine_location_id = str(seeded["locations"]["QUARANTINE-01"].id)
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-INSUFF", "LOT-INSUFF"
    )
    await _put_away(client, op_token, lot_id, containers[0], quarantine_location_id, "100.000000")
    await _release_lot(client, qa_token, lot_id)

    resp = await client.post(
        "/inventory/v1/transfers",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": containers[0],
            "from_location_id": quarantine_location_id,
            "to_location_id": released_location_id,
            "quantity": "999.000000",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


# --- INV-FR-010/011 reservation + the one signed operation -------------------------------------------


async def test_reservation_create_and_signed_release(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-RESV", "LOT-RESV"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")

    batch_id = await _create_batch(client, op_token, site_id, "RESV")

    resv_resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "30.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resv_resp.status_code == 200, resv_resp.text
    reservation_id = resv_resp.json()["aggregate_id"]

    availability = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    assert availability["items"][0]["available"] == "70.00000000"

    # release (give back) the reservation — the one Document 106 (row 46) signed operation, must be
    # independent of the requester (op_token).
    challenge = (
        await client.post(
            f"/inventory/v1/reservations/{reservation_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(qa_token),
        )
    ).json()
    release_resp = await client.post(
        f"/inventory/v1/reservations/{reservation_id}/release",
        json={
            "idempotency_key": idem(),
            "reservation_id": reservation_id,
            "expected_version": 1,
            "reason": "test release",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(qa_token),
    )
    assert release_resp.status_code == 200, release_resp.text
    assert release_resp.json()["signature_id"] is not None

    availability_after = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    assert availability_after["items"][0]["available"] == "100.00000000"


async def test_reservation_release_requires_independence_from_requester(client, db, seeded):
    """No demo role holds both inventory_reservation.create and .release, so a genuine independence
    violation (same person as requester and signer) is exercised by constructing the reservation directly
    with requested_by_user_id = the QA Releaser demo user, then attempting release as that same user via
    the real HTTP endpoint -- the independence check itself is what's under test here, not RBAC."""
    from app.modules.material import commands as material_commands

    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-SOD", "LOT-SOD"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "SOD")

    qa_releaser_user = seeded["users"]["qa.releaser"]
    await material_commands.create_inventory_reservation(
        db,
        material_commands.CreateInventoryReservationCommand(
            idempotency_key=idem(),
            batch_id=batch_id,
            material_id=material_id,
            site_id=site_id,
            quantity=Decimal("10.000000"),
            uom="kg",
        ),
        qa_releaser_user.id,
    )
    await db.commit()
    from app.modules.material.models import InventoryReservation

    reservation = (
        (await db.execute(select(InventoryReservation).where(InventoryReservation.batch_id == batch_id)))
        .scalars()
        .one()
    )
    reservation_id = str(reservation.id)

    challenge = (
        await client.post(
            f"/inventory/v1/reservations/{reservation_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(qa_token),
        )
    ).json()
    resp = await client.post(
        f"/inventory/v1/reservations/{reservation_id}/release",
        json={
            "idempotency_key": idem(),
            "reservation_id": reservation_id,
            "expected_version": 1,
            "reason": "test release",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_reservation_insufficient_available_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-OVERRESV", "LOT-OVERRESV", quantity="5.000000"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "5.000000")
    batch_id = await _create_batch(client, op_token, site_id, "OVERRESV")

    resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "999.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_reservation_excludes_quarantine_lot(client, db, seeded):
    """INV-FR-013/015: a still-quarantine (unreleased) lot is never selected — no hold entity needed,
    MaterialLot.status is the hold mechanism."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-QTN-EXCL", "LOT-QTN-EXCL"
    )
    batch_id = await _create_batch(client, op_token, site_id, "QTNEXCL")

    resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "1.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_simultaneous_reservations_do_not_over_reserve(client, db, seeded):
    """INV-FR-010 §10: two actors racing to reserve the same near-exhausted balance -- exactly one
    request can succeed once the remaining quantity is insufficient for both."""
    import asyncio

    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-RACE", "LOT-RACE", quantity="100.000000"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")
    batch_a = await _create_batch(client, op_token, site_id, "RACEA")
    batch_b = await _create_batch(client, op_token, site_id, "RACEB")

    async def _reserve(batch_id, quantity):
        return await client.post(
            "/inventory/v1/reservations",
            json={
                "idempotency_key": idem(),
                "batch_id": batch_id,
                "material_id": material_id,
                "site_id": str(site_id),
                "quantity": quantity,
                "uom": "kg",
            },
            headers=auth_headers(op_token),
        )

    resp_a, resp_b = await asyncio.gather(_reserve(batch_a, "60.000000"), _reserve(batch_b, "60.000000"))
    statuses = sorted([resp_a.status_code, resp_b.status_code])
    assert statuses == [200, 422], (resp_a.status_code, resp_a.text, resp_b.status_code, resp_b.text)

    availability = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    assert availability["items"][0]["available"] == "40.00000000"


async def test_reservation_excludes_expired_lot(client, db, seeded):
    """INV-FR-013: expired material is ineligible even when released and put away."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-EXP", "LOT-EXP", expiry_date="2020-01-01"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "EXP")

    availability = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    assert availability["items"] == []

    resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "1.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


# --- Client Topic 8 (SG-083) FEFO override ----------------------------------------------------------


async def test_fefo_override_requires_reason_then_pending_until_approved(client, db, seeded):
    """Client Topic 8: a non-FEFO lot override is recorded with a reason, but does not touch the ledger
    (no stock actually held) until a QA Releaser approves it."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id = await _create_material(client, site_id, code="RM-FEFO1", name="FEFO override material")
    older_lot_id, older_container_id = await _receive_lot_for_material(
        client, db, op_token, site_id, material_id, "LOT-FEFO1-OLD", expiry_date="2027-01-01"
    )
    await _release_lot(client, qa_token, older_lot_id)
    await _put_away(client, op_token, older_lot_id, older_container_id, released_location_id, "100.000000")
    newer_lot_id, newer_container_id = await _receive_lot_for_material(
        client, db, op_token, site_id, material_id, "LOT-FEFO1-NEW", expiry_date="2028-01-01"
    )
    await _release_lot(client, qa_token, newer_lot_id)
    await _put_away(client, op_token, newer_lot_id, newer_container_id, released_location_id, "100.000000")

    batch_id = await _create_batch(client, op_token, site_id, "FEFO1")

    no_reason_resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "10.000000",
            "uom": "kg",
            "override_lot_id": newer_lot_id,
        },
        headers=auth_headers(op_token),
    )
    assert no_reason_resp.status_code == 422, no_reason_resp.text
    assert no_reason_resp.json()["code"] == "VALIDATION_FAILED"

    resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "10.000000",
            "uom": "kg",
            "override_lot_id": newer_lot_id,
            "override_reason": "Oldest lot temporarily inaccessible in the warehouse",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    reservation_id = resp.json()["aggregate_id"]

    reservation = await db.get(InventoryReservation, uuid.UUID(reservation_id))
    assert reservation.status == "override_pending"
    assert reservation.fefo_overridden is True
    assert reservation.override_reason == "Oldest lot temporarily inaccessible in the warehouse"
    assert str(reservation.material_lot_id) == newer_lot_id
    assert str(reservation.fefo_default_lot_id) == older_lot_id

    # nothing reserved yet -- both lots show their full available quantity
    availability = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    assert {row["available"] for row in availability["items"]} == {"100.00000000"}

    # Independence check: no demo role holds both inventory_reservation.create and .approve_override, so
    # a genuine self-approval violation (same person as requester and approver) is exercised by
    # constructing a second override request directly with requested_by_user_id = the QA Releaser demo
    # user, then attempting approval as that same user via the real HTTP endpoint -- same technique
    # `test_reservation_release_requires_independence_from_requester` already uses for `.release`.
    from app.modules.material import commands as material_commands

    qa_releaser_user = seeded["users"]["qa.releaser"]
    await material_commands.create_inventory_reservation(
        db,
        material_commands.CreateInventoryReservationCommand(
            idempotency_key=idem(),
            batch_id=batch_id,
            material_id=material_id,
            site_id=site_id,
            quantity=Decimal("5.000000"),
            uom="kg",
            override_lot_id=uuid.UUID(newer_lot_id),
            override_reason="Self-approval independence check",
        ),
        qa_releaser_user.id,
    )
    await db.commit()
    self_requested_reservation = (
        (await db.execute(select(InventoryReservation).where(InventoryReservation.requested_by_user_id == qa_releaser_user.id)))
        .scalars()
        .one()
    )
    self_approve_resp = await client.post(
        f"/inventory/v1/reservations/{self_requested_reservation.id}/approve-override",
        json={
            "idempotency_key": idem(), "expected_version": 1, "reason": "self",
            "challenge_id": str(uuid.uuid4()), "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert self_approve_resp.status_code == 422, self_approve_resp.text

    challenge = (
        await client.post(
            f"/inventory/v1/reservations/{reservation_id}/signature-challenges",
            json={"action": "approve_override"},
            headers=auth_headers(qa_token),
        )
    ).json()
    approve_resp = await client.post(
        f"/inventory/v1/reservations/{reservation_id}/approve-override",
        json={
            "idempotency_key": idem(),
            "expected_version": 1,
            "reason": "Confirmed exception, approved",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["signature_id"] is not None

    reservation = await db.get(InventoryReservation, uuid.UUID(reservation_id))
    await db.refresh(reservation)
    assert reservation.status == "active"
    assert reservation.override_approved_by_user_id == seeded["users"]["qa.releaser"].id

    availability_after = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    by_lot = {row["material_lot_id"]: row["available"] for row in availability_after["items"]}
    assert by_lot[newer_lot_id] == "90.00000000"
    assert by_lot[older_lot_id] == "100.00000000"


async def test_fefo_override_rejected_leaves_ledger_untouched(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id = await _create_material(client, site_id, code="RM-FEFO2", name="FEFO reject material")
    older_lot_id, older_container_id = await _receive_lot_for_material(
        client, db, op_token, site_id, material_id, "LOT-FEFO2-OLD", quantity="50.000000", expiry_date="2027-01-01"
    )
    await _release_lot(client, qa_token, older_lot_id)
    await _put_away(client, op_token, older_lot_id, older_container_id, released_location_id, "50.000000")

    batch_id = await _create_batch(client, op_token, site_id, "FEFO2")
    resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "10.000000",
            "uom": "kg",
            "override_lot_id": older_lot_id,
            "override_reason": "Testing the reject path",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    reservation_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(
            f"/inventory/v1/reservations/{reservation_id}/signature-challenges",
            json={"action": "reject_override"},
            headers=auth_headers(qa_token),
        )
    ).json()
    reject_resp = await client.post(
        f"/inventory/v1/reservations/{reservation_id}/reject-override",
        json={
            "idempotency_key": idem(),
            "expected_version": 1,
            "reason": "Not a valid exception",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert reject_resp.status_code == 200, reject_resp.text
    assert reject_resp.json()["signature_id"] is not None

    reservation = await db.get(InventoryReservation, uuid.UUID(reservation_id))
    assert reservation.status == "override_rejected"

    availability = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    assert availability["items"][0]["available"] == "50.00000000"


async def test_fefo_override_queue_listed_for_approval(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id = await _create_material(client, site_id, code="RM-FEFO3", name="FEFO queue material")
    lot_id, container_id = await _receive_lot_for_material(
        client, db, op_token, site_id, material_id, "LOT-FEFO3", quantity="20.000000", expiry_date="2027-01-01"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "20.000000")

    batch_id = await _create_batch(client, op_token, site_id, "FEFO3")
    resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "5.000000",
            "uom": "kg",
            "override_lot_id": lot_id,
            "override_reason": "Queue visibility test",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    reservation_id = resp.json()["aggregate_id"]

    queue = (
        await client.get(
            "/inventory/v1/reservations", params={"status": "override_pending"}, headers=auth_headers(qa_token)
        )
    ).json()
    ids = [item["id"] for item in queue["items"]]
    assert reservation_id in ids
    row = next(item for item in queue["items"] if item["id"] == reservation_id)
    assert row["fefo_overridden"] is True
    assert row["override_reason"] == "Queue visibility test"


# --- INV-FR-023/024 container split / merge -----------------------------------------------------------


async def test_split_container_conserves_quantity(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-SPLIT", "LOT-SPLIT", quantity="90.000000"
    )
    container_id = containers[0]

    resp = await client.post(
        f"/inventory/v1/containers/{container_id}/split",
        json={
            "idempotency_key": idem(),
            "container_id": container_id,
            "expected_version": 1,
            "split_quantities": ["30.000000", "30.000000", "30.000000"],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    remaining = (
        (await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot_id)))
        .scalars()
        .all()
    )
    original = next(c for c in remaining if str(c.id) == container_id)
    children = [c for c in remaining if str(c.id) != container_id]
    assert original.container_status == "split"
    assert original.current_quantity == Decimal("0.000000")
    assert len(children) == 3
    assert sum(c.current_quantity for c in children) == Decimal("90.000000")
    assert all(c.parent_container_id == original.id for c in children)


async def test_split_container_wires_split_from_genealogy_edge(client, db, seeded):
    """SG-085 Task 2 (2026-09-23): split_container now writes a SPLIT_FROM edge per child, the direct
    catalogue match for GEN-FR-015 ("one lot split into many")."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-SPLIT-GEN", "LOT-SPLIT-GEN", quantity="60.000000"
    )
    container_id = containers[0]

    resp = await client.post(
        f"/inventory/v1/containers/{container_id}/split",
        json={
            "idempotency_key": idem(),
            "container_id": container_id,
            "expected_version": 1,
            "split_quantities": ["20.000000", "20.000000", "20.000000"],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    remaining = (
        (await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot_id)))
        .scalars()
        .all()
    )
    original = next(c for c in remaining if str(c.id) == container_id)
    children = [c for c in remaining if str(c.id) != container_id]
    assert len(children) == 3

    [parent_node] = await genealogy_service.lookup(db, site_id, business_ref=original.container_code)
    descendants = await genealogy_service.get_descendants(db, parent_node.id)
    descendant_record_ids = {n.authoritative_record_id for n in descendants["nodes"]}
    assert {c.id for c in children} == descendant_record_ids
    assert all(e.edge_type == "SPLIT_FROM" for e in descendants["edges"])
    assert {e.quantity for e in descendants["edges"]} == {Decimal("20.000000")}


async def test_split_quantity_mismatch_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-SPLITBAD", "LOT-SPLITBAD", quantity="90.000000"
    )
    container_id = containers[0]

    resp = await client.post(
        f"/inventory/v1/containers/{container_id}/split",
        json={
            "idempotency_key": idem(),
            "container_id": container_id,
            "expected_version": 1,
            "split_quantities": ["10.000000", "10.000000"],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_merge_incompatible_status_rejected(client, db, seeded):
    """INV-FR-024: containers must share the same effective quality status to merge."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-MERGEBAD", "LOT-MERGEBAD", container_count=2, quantity="60.000000"
    )
    # partially reject one container so it diverges in effective status from its sibling
    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "reject"},
            headers=auth_headers(qa_token),
        )
    ).json()
    resp = await client.post(
        f"/materials/v1/lots/{lot_id}/reject",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "reason": "partial container reject for merge-incompatibility test",
            "container_ids": [containers[0]],
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 200, resp.text

    merge_resp = await client.post(
        "/inventory/v1/containers/merge",
        json={
            "idempotency_key": idem(),
            "source_container_ids": containers,
            "new_container_code": "LOT-MERGEBAD-MERGED",
        },
        headers=auth_headers(op_token),
    )
    assert merge_resp.status_code == 422
    assert merge_resp.json()["code"] == "VALIDATION_FAILED"


async def test_merge_compatible_containers(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-MERGEOK", "LOT-MERGEOK", container_count=2, quantity="60.000000"
    )

    resp = await client.post(
        "/inventory/v1/containers/merge",
        json={
            "idempotency_key": idem(),
            "source_container_ids": containers,
            "new_container_code": "LOT-MERGEOK-MERGED",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    all_containers = (
        (await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot_id)))
        .scalars()
        .all()
    )
    merged = [c for c in all_containers if c.container_status == "active"]
    sources = [c for c in all_containers if c.container_status == "merged"]
    assert len(merged) == 1
    assert len(sources) == 2
    assert merged[0].current_quantity == Decimal("60.000000")


async def test_merge_containers_wires_merged_from_genealogy_edge(client, db, seeded):
    """Client_Decisions_Neededanswers Topic 2 / SG-085: merge_containers now writes a MERGED_FROM edge
    per source container into the new container's genealogy node -- the reverse shape of
    split_container's SPLIT_FROM, closing the "merge investigated, not built" half of SG-085."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-MERGE-GEN", "LOT-MERGE-GEN", container_count=2, quantity="60.000000"
    )

    resp = await client.post(
        "/inventory/v1/containers/merge",
        json={
            "idempotency_key": idem(),
            "source_container_ids": containers,
            "new_container_code": "LOT-MERGE-GEN-MERGED",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    all_containers = (
        (await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot_id)))
        .scalars()
        .all()
    )
    merged = next(c for c in all_containers if c.container_status == "active")
    sources = [c for c in all_containers if c.container_status == "merged"]
    assert len(sources) == 2

    [merged_node] = await genealogy_service.lookup(db, site_id, business_ref=merged.container_code)
    ancestors = await genealogy_service.get_ancestors(db, merged_node.id)
    ancestor_record_ids = {n.authoritative_record_id for n in ancestors["nodes"]}
    assert {c.id for c in sources} == ancestor_record_ids
    assert all(e.edge_type == "MERGED_FROM" for e in ancestors["edges"])
    assert {e.quantity for e in ancestors["edges"]} == {Decimal("30.000000")}


# --- INV-FR-020/022 cycle count -------------------------------------------------------------------


async def test_cycle_count_no_variance_recorded_without_approval(client, db, seeded):
    """A count that matches on-hand has nothing to approve -- no InventoryAdjustmentRequest is created."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-CYCLEMATCH", "LOT-CYCLEMATCH"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")

    resp = await client.post(
        "/inventory/v1/cycle-counts",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": containers[0],
            "location_id": released_location_id,
            "counted_quantity": "100.000000",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    ledger = (await client.get(f"/inventory/v1/lots/{lot_id}/ledger", headers=auth_headers(qa_token))).json()
    types = [row["transaction_type"] for row in ledger["items"]]
    assert "ADJUST_NEGATIVE" not in types and "ADJUST_POSITIVE" not in types


async def test_cycle_count_variance_requires_reason_and_second_person_approval(client, db, seeded):
    """Client Topic 7 Q13 (SG-084, project-owner-directed): a counted quantity that differs from on-hand
    opens an InventoryAdjustmentRequest instead of mutating the ledger directly -- the ledger only
    changes once a second, independent person approves it (same Document 106 row 55 signature
    CON-FR-013/014 already enforces for the pre-existing adjustment-request flow)."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-CYCLE", "LOT-CYCLE"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")

    # reason is required once there's a variance
    no_reason_resp = await client.post(
        "/inventory/v1/cycle-counts",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": containers[0],
            "location_id": released_location_id,
            "counted_quantity": "97.500000",
        },
        headers=auth_headers(op_token),
    )
    assert no_reason_resp.status_code == 422, no_reason_resp.text
    assert no_reason_resp.json()["code"] == "VALIDATION_FAILED"

    resp = await client.post(
        "/inventory/v1/cycle-counts",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": containers[0],
            "location_id": released_location_id,
            "counted_quantity": "97.500000",
            "reason": "physical count variance",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    request_id = resp.json()["aggregate_id"]

    request = await db.get(InventoryAdjustmentRequest, uuid.UUID(request_id))
    assert request.status == "requested"
    assert request.expected_quantity == Decimal("100.000000")
    assert request.observed_quantity == Decimal("97.500000")
    assert request.requested_by_user_id == seeded["users"]["operator1"].id

    # ledger is untouched until approved
    ledger_before = (await client.get(f"/inventory/v1/lots/{lot_id}/ledger", headers=auth_headers(qa_token))).json()
    assert "ADJUST_NEGATIVE" not in [row["transaction_type"] for row in ledger_before["items"]]

    challenge = (
        await client.post(
            f"/inventory/v1/adjustments/{request_id}/signature-challenges",
            json={"action": "approve"},
            headers=auth_headers(qa_token),
        )
    ).json()
    approve_resp = await client.post(
        f"/inventory/v1/adjustments/{request_id}/approve",
        json={
            "idempotency_key": idem(),
            "expected_version": 1,
            "reason": "confirmed by second count",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert approve_resp.status_code == 200, approve_resp.text
    assert approve_resp.json()["signature_id"] is not None

    ledger = (await client.get(f"/inventory/v1/lots/{lot_id}/ledger", headers=auth_headers(qa_token))).json()
    types = [row["transaction_type"] for row in ledger["items"]]
    assert "RECEIPT" in types
    assert "ADJUST_NEGATIVE" in types
    # history is never rewritten -- the RECEIPT row for 100 is still present alongside the new adjustment
    receipt_row = next(row for row in ledger["items"] if row["transaction_type"] == "RECEIPT")
    assert receipt_row["quantity"] == "100.00000000"


async def test_cycle_count_negative_counted_quantity_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    quarantine_location_id = str(seeded["locations"]["QUARANTINE-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-CYCLENEG", "LOT-CYCLENEG"
    )

    resp = await client.post(
        "/inventory/v1/cycle-counts",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": containers[0],
            "location_id": quarantine_location_id,
            "counted_quantity": "-5.000000",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


# --- Client Topic 7 Q14 (SG-084) location lock during a physical count --------------------------------


async def test_lock_location_requires_rbac_and_reason(client, db, seeded):
    op_token = await login(client, "operator1")
    supervisor_token = await login(client, "supervisor1")
    location_id = str(seeded["locations"]["QUARANTINE-01"].id)

    forbidden_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{location_id}/lock",
        json={"idempotency_key": idem(), "expected_version": 1, "reason": "physical count"},
        headers=auth_headers(op_token),
    )
    assert forbidden_resp.status_code == 403, forbidden_resp.text

    no_reason_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{location_id}/lock",
        json={"idempotency_key": idem(), "expected_version": 1, "reason": "   "},
        headers=auth_headers(supervisor_token),
    )
    assert no_reason_resp.status_code == 422, no_reason_resp.text

    lock_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{location_id}/lock",
        json={"idempotency_key": idem(), "expected_version": 1, "reason": "physical count"},
        headers=auth_headers(supervisor_token),
    )
    assert lock_resp.status_code == 200, lock_resp.text

    supervisor_id = seeded["users"]["supervisor1"].id
    location = await db.get(WarehouseLocation, uuid.UUID(location_id))
    await db.refresh(location)
    assert location.locked is True
    assert location.lock_reason == "physical count"
    assert location.locked_by_user_id == supervisor_id

    # already-locked lock attempt is rejected
    already_locked_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{location_id}/lock",
        json={"idempotency_key": idem(), "expected_version": 2, "reason": "again"},
        headers=auth_headers(supervisor_token),
    )
    assert already_locked_resp.status_code == 409, already_locked_resp.text
    assert already_locked_resp.json()["code"] == "INVALID_TRANSITION"

    unlock_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{location_id}/unlock",
        json={"idempotency_key": idem(), "expected_version": 2, "reason": "count complete"},
        headers=auth_headers(supervisor_token),
    )
    assert unlock_resp.status_code == 200, unlock_resp.text

    await db.refresh(location)
    assert location.locked is False
    assert location.lock_reason is None


async def test_locked_location_blocks_transfer_in_and_out(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    supervisor_token = await login(client, "supervisor1")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)
    quarantine_location_id = str(seeded["locations"]["QUARANTINE-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-LOCK", "LOT-LOCK"
    )
    await _release_lot(client, qa_token, lot_id)

    lock_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{released_location_id}/lock",
        json={"idempotency_key": idem(), "expected_version": 1, "reason": "physical count"},
        headers=auth_headers(supervisor_token),
    )
    assert lock_resp.status_code == 200, lock_resp.text

    blocked_resp = await client.post(
        "/inventory/v1/transfers",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": containers[0],
            "from_location_id": None,
            "to_location_id": released_location_id,
            "quantity": "100.000000",
        },
        headers=auth_headers(op_token),
    )
    assert blocked_resp.status_code == 409, blocked_resp.text
    assert blocked_resp.json()["code"] == "LOCATION_LOCKED"

    unlock_resp = await client.post(
        f"/inventory/v1/warehouse-locations/{released_location_id}/unlock",
        json={"idempotency_key": idem(), "expected_version": 2, "reason": "count complete"},
        headers=auth_headers(supervisor_token),
    )
    assert unlock_resp.status_code == 200, unlock_resp.text

    put_away_resp = await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")
    assert put_away_resp["aggregate_id"]

    # now lock the location the stock is actually in and confirm a transfer OUT is blocked too
    lock_resp_2 = await client.post(
        f"/inventory/v1/warehouse-locations/{released_location_id}/lock",
        json={"idempotency_key": idem(), "expected_version": 3, "reason": "physical count again"},
        headers=auth_headers(supervisor_token),
    )
    assert lock_resp_2.status_code == 200, lock_resp_2.text

    blocked_out_resp = await client.post(
        "/inventory/v1/transfers",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": containers[0],
            "from_location_id": released_location_id,
            "to_location_id": quarantine_location_id,
            "quantity": "10.000000",
        },
        headers=auth_headers(op_token),
    )
    assert blocked_out_resp.status_code == 409, blocked_out_resp.text
    assert blocked_out_resp.json()["code"] == "LOCATION_LOCKED"


# --- INV-FR-006/section 8: direct UPDATE/DELETE on the immutable ledger is refused ---------------------


async def test_inventory_transaction_update_refused_at_privilege_level(client, db, seeded):
    """Migration 0028 grants the runtime app role SELECT/INSERT/TRUNCATE only on inventory_transactions
    (no UPDATE/DELETE) -- the same append-only discipline as material_quality_dispositions."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-PRIV", "LOT-PRIV"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")

    txn = (
        (await db.execute(select(InventoryTransaction).where(InventoryTransaction.material_lot_id == lot_id)))
        .scalars()
        .first()
    )
    with pytest.raises(DBAPIError, match="(?i)permission denied|insufficient"):
        await db.execute(
            InventoryTransaction.__table__.update()
            .where(InventoryTransaction.id == txn.id)
            .values(quantity=Decimal("1.00000000"))
        )
        await db.flush()
    await db.rollback()


# --- read-only endpoints ---------------------------------------------------------------------------


async def test_erp_reconciliation_never_fabricates_erp_side(client, db, seeded):
    """INV-FR-028: no ERP integration exists (WP-07, SG-082) — the ERP side is null, not guessed."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-ERP", "LOT-ERP"
    )

    resp = await client.get("/inventory/v1/reconciliation/erp", params={"lot_id": lot_id}, headers=auth_headers(op_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["erp_source_configured"] is False
    assert body["erp_on_hand"] is None
    assert body["mismatch_flagged"] is None


# --- module-suite: idempotency / stale version / unauthorized -----------------------------------------


async def test_duplicate_reservation_idempotency_key_returns_same_receipt(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-IDEM", "LOT-IDEM"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "IDEM")

    key = idem()
    body = {
        "idempotency_key": key,
        "batch_id": batch_id,
        "material_id": material_id,
        "site_id": str(site_id),
        "quantity": "10.000000",
        "uom": "kg",
    }
    first = await client.post("/inventory/v1/reservations", json=body, headers=auth_headers(op_token))
    second = await client.post("/inventory/v1/reservations", json=body, headers=auth_headers(op_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


async def test_reservation_release_stale_version_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-STALE", "LOT-STALE"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "STALE")

    reservation_id = (
        await client.post(
            "/inventory/v1/reservations",
            json={
                "idempotency_key": idem(),
                "batch_id": batch_id,
                "material_id": material_id,
                "site_id": str(site_id),
                "quantity": "10.000000",
                "uom": "kg",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    challenge = (
        await client.post(
            f"/inventory/v1/reservations/{reservation_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(qa_token),
        )
    ).json()
    resp = await client.post(
        f"/inventory/v1/reservations/{reservation_id}/release",
        json={
            "idempotency_key": idem(),
            "reservation_id": reservation_id,
            "expected_version": 999,
            "reason": "test release",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_reservation_release_without_signature_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-NOSIG", "LOT-NOSIG"
    )
    await _release_lot(client, qa_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "NOSIG")

    reservation_id = (
        await client.post(
            "/inventory/v1/reservations",
            json={
                "idempotency_key": idem(),
                "batch_id": batch_id,
                "material_id": material_id,
                "site_id": str(site_id),
                "quantity": "10.000000",
                "uom": "kg",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    import uuid as uuid_module

    resp = await client.post(
        f"/inventory/v1/reservations/{reservation_id}/release",
        json={
            "idempotency_key": idem(),
            "reservation_id": reservation_id,
            "expected_version": 1,
            "reason": "test release",
            "challenge_id": str(uuid_module.uuid4()),
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_CHALLENGE_INVALID"


async def test_reservation_excludes_suspended_supplier_lot(client, db, seeded):
    """SG-097 (MAT-013 half, 2026-09-22): a released, put-away, non-expired lot from a supplier that is
    later suspended stops being reservable -- distinct from RCV-FR-005's own receipt-time check (which
    only ever runs once, at examine), and from the receipt-gate half of SG-097 (which only blocks a *new*
    receipt from a suspended source). Reuses `_is_eligible`'s existing `supplier_status != "approved"`
    check, the exact inequality RCV-FR-005 already established for this same field."""
    import uuid as _uuid

    async with db.begin():
        await _make_admin(db, seeded, "admin.invsusp")
    admin_token = await login(client, "admin.invsusp")
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    supplier_id = await _create_supplier(client, admin_token, "SUP-INV-SUSP")
    async with db.begin():
        supplier = await db.get(Supplier, _uuid.UUID(supplier_id))
        supplier.status = "approved"

    material_id = await _create_material(client, site_id, code="MAT-INV-SUSP")
    receipt_id = await _create_receipt(
        client, op_token, site_id, material_id, receipt_number="RCPT-INV-SUSP", supplier_id=supplier_id
    )
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-INV-SUSP", container_count=1)
    async with db.begin():
        lot = (await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == "LOT-INV-SUSP"))).scalar_one()
        container = (
            await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot.id))
        ).scalar_one()
    await _release_lot(client, qa_token, str(lot.id))
    await _put_away(client, op_token, str(lot.id), str(container.id), released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "INVSUSP")

    # While the supplier is still approved, the lot is a normal reservation candidate.
    availability = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    assert len(availability["items"]) == 1

    async with db.begin():
        supplier = await db.get(Supplier, _uuid.UUID(supplier_id))
        supplier.status = "suspended"

    availability = (
        await client.get(
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)},
            headers=auth_headers(op_token),
        )
    ).json()
    assert availability["items"] == []

    resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "material_id": material_id,
            "site_id": str(site_id),
            "quantity": "1.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_unauthenticated_reservation_request_rejected(client):
    resp = await client.post(
        "/inventory/v1/reservations",
        json={
            "idempotency_key": idem(),
            "batch_id": "00000000-0000-0000-0000-000000000000",
            "material_id": "00000000-0000-0000-0000-000000000000",
            "site_id": "00000000-0000-0000-0000-000000000000",
            "quantity": "1.000000",
            "uom": "kg",
        },
    )
    assert resp.status_code == 401
