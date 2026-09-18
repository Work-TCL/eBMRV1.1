"""Document 20 (SPEC-MAT-002B) — Inventory, Lot/Container & Warehouse. Extends the Document 19 receipt/
examine/release flow with: put-away (transfer with no from_location, INV-FR-008), reservation + the one
signed operation (release, Document 106 row 46, INV-FR-010/011), transfer between locations (INV-FR-008),
container split/merge (INV-FR-023/024), cycle count (INV-FR-020/022), and the read-only availability/
ledger/reconciliation endpoints (INV-FR-003/029/028)."""

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.modules.material.models import InventoryTransaction, MaterialContainer, MaterialLot
from tests.conftest import auth_headers, idem, login


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
            "damage_observed": False,
            "seal_broken": False,
            "contamination_observed": False,
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

    ledger = (await client.get(f"/inventory/v1/lots/{lot_id}/ledger")).json()
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
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)}
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
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)}
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
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)}
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
            "/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)}
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


# --- INV-FR-020/022 cycle count -------------------------------------------------------------------


async def test_cycle_count_records_discrepancy_and_preserves_history(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "MAT-CYCLE", "LOT-CYCLE"
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
            "counted_quantity": "97.500000",
            "reason": "physical count variance",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    ledger = (await client.get(f"/inventory/v1/lots/{lot_id}/ledger")).json()
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

    resp = await client.get("/inventory/v1/reconciliation/erp", params={"lot_id": lot_id})
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
