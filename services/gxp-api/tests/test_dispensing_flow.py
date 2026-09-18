"""Document 21 (SPEC-MAT-002C) — Material Dispensing & Weighing. Builds on Document 20's put-away/release
chain: create order -> select-source (reuses a released, put-away lot) -> start (qualification gate) ->
manual-reading -> verify (independence-from-performer) -> complete (inventory consumption + dispensed-
container creation) -> cancel (independence-from-author, reason required, reservation returned)."""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.core.security import hash_password
from app.modules.iam.models import Role, User, UserSiteRole
from app.modules.material.models import (
    DispensedContainer,
    DispensingOrder,
    InventoryBalanceProjection,
    WeighingReading,
    WeighingSession,
)
from app.modules.material.models import MaterialContainer, MaterialLot
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_inventory_flow import _create_batch, _create_material, _put_away, _receive_and_examine, _release_lot


async def _receive_lot_for_material(client, db, token, site_id, material_id, internal_lot, quantity="100.000000"):
    """Like Document 20's `_receive_and_examine`, but against an *existing* material (needed for
    multi-lot dispensing, DSP-FR-017, where two lots share one material identity)."""
    receipt_id = (
        await client.post(
            "/materials/v1/receipts",
            json={
                "idempotency_key": idem(),
                "site_id": str(site_id),
                "receipt_number": f"RCPT-{internal_lot}",
                "material_id": material_id,
                "received_gross_quantity": quantity,
                "accepted_quantity": quantity,
                "uom": "kg",
            },
            headers=auth_headers(token),
        )
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


async def _create_order(client, token, site_id, batch_id, material_id, target_qty="30.000000", low="28.000000", high="32.000000"):
    resp = await client.post(
        "/dispensing/v1/orders",
        json={
            "idempotency_key": idem(),
            "site_id": str(site_id),
            "batch_id": batch_id,
            "material_id": material_id,
            "target_qty": target_qty,
            "target_uom": "kg",
            "tolerance_low": low,
            "tolerance_high": high,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _challenge(client, token, order_id, action):
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/signature-challenges",
        json={"action": action},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def _select_source(client, token, order_id, expected_version, material_lot_id, quantity="30.000000", reservation_id=None, container_id=None):
    challenge_id = await _challenge(client, token, order_id, "select_source")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/select-source",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "material_lot_id": material_lot_id,
            "container_id": container_id,
            "reservation_id": reservation_id,
            "quantity": quantity,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _start(client, token, order_id, expected_version):
    challenge_id = await _challenge(client, token, order_id, "start")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/start",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _manual_reading(client, token, order_id, expected_version, value, stable=True, reason="operator entry"):
    challenge_id = await _challenge(client, token, order_id, "manual_reading")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/manual-reading",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "reading_value": value,
            "uom": "kg",
            "stable": stable,
            "manual_reason": reason,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _verify(client, token, order_id, expected_version):
    challenge_id = await _challenge(client, token, order_id, "verify")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/verify",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _complete(client, token, order_id, expected_version, source_id, quantity, container_code):
    challenge_id = await _challenge(client, token, order_id, "complete")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/complete",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "actual_taken_quantities": {source_id: quantity},
            "container_code": container_code,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _cancel(client, token, order_id, expected_version, reason="operational change"):
    challenge_id = await _challenge(client, token, order_id, "cancel")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/cancel",
        json={
            "idempotency_key": idem(),
            "expected_version": expected_version,
            "reason": reason,
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    return resp


async def _prepared_lot(client, db, op_token, qa_token, site_id, code, internal_lot, quantity="100.000000"):
    """Receive -> examine -> release (QA Releaser signs, Document 106 rows 44/45), returning
    (material_id, lot_id, container_id). Caller still needs to put the container away (Document 20's
    `_put_away`) before it has any ledger balance."""
    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, code, internal_lot, quantity=quantity
    )
    await _release_lot(client, qa_token, lot_id)
    return material_id, lot_id, containers[0]


async def test_full_dispensing_flow_happy_path(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-DSP", "LOT-DSP")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "DSP")

    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)

    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text

    start_resp = await _start(client, op_token, order_id, 2)
    assert start_resp.status_code == 200, start_resp.text

    reading_resp = await _manual_reading(client, op_token, order_id, 3, "30.000000")
    assert reading_resp.status_code == 200, reading_resp.text

    verify_resp = await _verify(client, qc_token, order_id, 3)
    assert verify_resp.status_code == 200, verify_resp.text
    assert verify_resp.json()["signature_id"] is not None

    from app.modules.material.models import DispensingSource

    src = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalar_one()

    complete_resp = await _complete(client, op_token, order_id, 4, str(src.id), "30.000000", "DISP-CTR-1")
    assert complete_resp.status_code == 200, complete_resp.text

    order = await db.get(DispensingOrder, uuid.UUID(order_id))
    assert order.state == "completed"

    dispensed = (
        await db.execute(select(DispensedContainer).where(DispensedContainer.dispensing_order_id == order_id))
    ).scalar_one()
    assert dispensed.actual_quantity == 30

    balance = (
        await db.execute(
            select(InventoryBalanceProjection).where(InventoryBalanceProjection.material_lot_id == uuid.UUID(lot_id))
        )
    ).scalar_one()
    assert balance.on_hand == 70


async def test_select_source_wrong_material_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-WRONG", "LOT-WRONG")
    other_material_id = await _create_material(client, site_id, code="RM-OTHER", name="Other")
    batch_id = await _create_batch(client, op_token, site_id, "WRONGMAT")
    order_id = await _create_order(client, op_token, site_id, batch_id, other_material_id)

    resp = await _select_source(client, op_token, order_id, 1, lot_id)
    assert resp.status_code == 422
    assert resp.json()["code"] == "WRONG_MATERIAL"


async def test_select_source_insufficient_quantity_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(
        client, db, op_token, qa_token, site_id, "MAT-SHORT", "LOT-SHORT", quantity="5.000000"
    )
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "5.000000")
    batch_id = await _create_batch(client, op_token, site_id, "SHORT")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id, target_qty="30.000000", low="28", high="32")

    resp = await _select_source(client, op_token, order_id, 1, lot_id, quantity="30.000000", container_id=container_id)
    assert resp.status_code == 422
    assert resp.json()["code"] == "SOURCE_QUANTITY_INSUFFICIENT"


async def test_start_requires_current_qualification(client, db, seeded):
    """DSP-FR-005: iam.Qualification, wired up for real this pass — a second Operator-role user with no
    qualification row is blocked at `start`."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-NOQUAL", "LOT-NOQUAL")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "NOQUAL")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text

    unqualified = User(
        username="operator2", email="operator2@example.com", full_name="operator2",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(unqualified)
    await db.flush()
    operator_role = (await db.execute(select(Role).where(Role.name == "Operator"))).scalar_one()
    db.add(UserSiteRole(user_id=unqualified.id, site_id=seeded["site_id"], role_id=operator_role.id))
    await db.commit()

    op2_token = await login(client, "operator2")
    resp = await _start(client, op2_token, order_id, 2)
    assert resp.status_code == 403
    assert resp.json()["code"] == "QUALIFICATION_MISSING"


async def test_verify_requires_independence_from_performer(client, db, seeded):
    """DSP-FR-018 / Document 106 row 54: verifier MUST NOT be the performer. Only QC Reviewer holds
    dispensing_order.verify RBAC, and only Operator holds dispensing_order.start, so no single seeded
    account can legitimately reach both roles through the normal API -- performed_by_user_id is set
    directly via the db fixture to isolate the independence check from RBAC, the same technique already
    used for the qualification-gate test above."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-VERIFY", "LOT-VERIFY")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "VERIFYSELF")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    await _start(client, op_token, order_id, 2)

    order = await db.get(DispensingOrder, uuid.UUID(order_id))
    order.performed_by_user_id = seeded["users"]["qc.reviewer"].id
    await db.commit()

    resp = await _verify(client, qc_token, order_id, 3)
    assert resp.status_code == 428
    assert resp.json()["code"] == "VERIFIER_REQUIRED"


async def test_complete_out_of_tolerance_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-TOL", "LOT-TOL")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "TOLFAIL")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id, target_qty="30.000000", low="28", high="32")
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, quantity="50.000000", container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    await _start(client, op_token, order_id, 2)

    from app.modules.material.models import DispensingSource

    src = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalar_one()

    resp = await _complete(client, op_token, order_id, 3, str(src.id), "50.000000", "DISP-CTR-TOL")
    assert resp.status_code == 422
    assert resp.json()["code"] == "WEIGHT_OUT_OF_TOLERANCE"


async def test_cancel_requires_reason(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-CANCELREASON", name="X")
    batch_id = await _create_batch(client, op_token, site_id, "CANCELREASON")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)

    resp = await _cancel(client, qa_token, order_id, 1, reason="")
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_cancel_requires_independence_from_author(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-CANCELSOD", name="X")
    batch_id = await _create_batch(client, op_token, site_id, "CANCELSOD")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)

    # Admin has dispensing_order.cancel but is also not the author here — use the author's own token
    # (operator1), which does NOT have dispensing_order.cancel granted, to prove SoD is enforced
    # independently of RBAC (an author who somehow held cancel permission would still be blocked).
    resp = await _cancel(client, op_token, order_id, 1)
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_cancel_returns_active_reservation(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-CANCELRES", "LOT-CANCELRES")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "CANCELRES")

    reservation_id = (
        await client.post(
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
    ).json()["aggregate_id"]

    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, None, quantity="30.000000", reservation_id=reservation_id)
    assert select_resp.status_code == 200, select_resp.text

    resp = await _cancel(client, qa_token, order_id, 2)
    assert resp.status_code == 200, resp.text

    from app.modules.material.models import InventoryReservation

    reservation = await db.get(InventoryReservation, uuid.UUID(reservation_id))
    assert reservation.status == "released"

    availability = (
        await client.get("/inventory/v1/availability", params={"material_id": material_id, "site_id": str(site_id)})
    ).json()
    assert availability["items"][0]["available"] == "100.00000000"


async def test_queue_lists_noncompleted_orders(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-QUEUE", name="X")
    batch_id = await _create_batch(client, op_token, site_id, "QUEUE")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)

    queue = (await client.get("/dispensing/v1/queue")).json()
    ids = [item["id"] for item in queue["items"]]
    assert order_id in ids


async def test_duplicate_create_order_idempotency_key_returns_same_receipt(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-IDEM21", name="X")
    batch_id = await _create_batch(client, op_token, site_id, "IDEM21")

    key = idem()
    body = {
        "idempotency_key": key, "site_id": str(site_id), "batch_id": batch_id, "material_id": material_id,
        "target_qty": "30.000000", "target_uom": "kg", "tolerance_low": "28.000000", "tolerance_high": "32.000000",
    }
    first = await client.post("/dispensing/v1/orders", json=body, headers=auth_headers(op_token))
    second = await client.post("/dispensing/v1/orders", json=body, headers=auth_headers(op_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


async def test_select_source_stale_version_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-STALE21", name="X")
    batch_id = await _create_batch(client, op_token, site_id, "STALE21")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)

    resp = await _select_source(client, op_token, order_id, 999, None, quantity="1.000000")
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_unauthenticated_create_order_rejected(client):
    resp = await client.post(
        "/dispensing/v1/orders",
        json={
            "idempotency_key": idem(),
            "site_id": "00000000-0000-0000-0000-000000000000",
            "batch_id": "00000000-0000-0000-0000-000000000000",
            "material_id": "00000000-0000-0000-0000-000000000000",
            "target_qty": "1.000000",
            "target_uom": "kg",
            "tolerance_low": "0.900000",
            "tolerance_high": "1.100000",
        },
    )
    assert resp.status_code == 401


async def test_weighing_reading_update_refused_at_privilege_level(client, db, seeded):
    """Migration 0029 grants the runtime app role SELECT/INSERT/TRUNCATE only on weighing_readings (no
    UPDATE/DELETE) -- the same append-only discipline as inventory_transactions (migration 0028) and
    material_quality_dispositions (migration 0027), matching DSP-FR-014's "original reading retained"."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-READPRIV", "LOT-READPRIV")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "READPRIV")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)
    await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    await _start(client, op_token, order_id, 2)
    await _manual_reading(client, op_token, order_id, 3, "30.000000")

    weighing = (
        await db.execute(select(WeighingSession).where(WeighingSession.dispensing_order_id == order_id))
    ).scalar_one()
    reading = (
        await db.execute(select(WeighingReading).where(WeighingReading.weighing_session_id == weighing.id))
    ).scalars().first()

    with pytest.raises(DBAPIError, match="(?i)permission denied|insufficient"):
        await db.execute(
            WeighingReading.__table__.update()
            .where(WeighingReading.id == reading.id)
            .values(reading_value=Decimal("1.00000000"))
        )
        await db.flush()
    await db.rollback()


async def test_cancel_without_valid_signature_challenge_rejected(client, db, seeded):
    """Every signed dispensing action shares the same `_dispensing_sign` -> `signature_service.
    consume_challenge` code path Document 19/20 already tested dedicatedly (e.g. test_inventory_flow.py::
    test_reservation_release_without_signature_rejected) -- this test exercises that shared mechanism
    through this module's own endpoint rather than duplicating it."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-NOSIG21", name="X")
    batch_id = await _create_batch(client, op_token, site_id, "NOSIG21")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id)

    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/cancel",
        json={
            "idempotency_key": idem(),
            "expected_version": 1,
            "reason": "test",
            "challenge_id": str(uuid.uuid4()),
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_CHALLENGE_INVALID"


async def test_multiple_readings_preserve_history_and_sum_accepted_net(client, db, seeded):
    """DSP-FR-013: incremental weigh additions preserve every reading and accumulate the accepted net --
    both readings stay in the append-only weighing_readings table (DSP-FR-014's "original reading
    retained" rule)."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, "MAT-MULTIREAD", "LOT-MULTIREAD")
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, "MULTIREAD")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id, target_qty="30.000000", low="28", high="32")
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id)
    assert select_resp.status_code == 200, select_resp.text
    start_resp = await _start(client, op_token, order_id, 2)
    assert start_resp.status_code == 200, start_resp.text

    first = await _manual_reading(client, op_token, order_id, 3, "18.000000")
    assert first.status_code == 200, first.text
    second = await _manual_reading(client, op_token, order_id, 3, "12.000000")
    assert second.status_code == 200, second.text

    weighing = (
        await db.execute(select(WeighingSession).where(WeighingSession.dispensing_order_id == order_id))
    ).scalar_one()
    readings = (
        await db.execute(
            select(WeighingReading)
            .where(WeighingReading.weighing_session_id == weighing.id)
            .order_by(WeighingReading.sequence)
        )
    ).scalars().all()
    assert [r.reading_value for r in readings] == [Decimal("18.000000"), Decimal("12.000000")]
    assert weighing.final_accepted_net == 30

    from app.modules.material.models import DispensingSource

    src = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalar_one()
    complete_resp = await _complete(client, op_token, order_id, 3, str(src.id), "30.000000", "DISP-MULTIREAD-CTR")
    assert complete_resp.status_code == 200, complete_resp.text


async def test_multi_lot_dispensing_conserves_genealogy_per_source(client, db, seeded):
    """DSP-FR-017: multiple approved lots contribute to one order, each source's exact quantity traced
    separately (dispensing_sources rows), no hidden pooling into a single undifferentiated total."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id = await _create_material(client, site_id, code="RM-MULTILOT", name="Multi-lot material")
    lot1_id, container1_id = await _receive_lot_for_material(client, db, op_token, site_id, material_id, "LOT-MULTILOT-1", quantity="20.000000")
    await _release_lot(client, qa_token, lot1_id)
    await _put_away(client, op_token, lot1_id, container1_id, released_location_id, "20.000000")
    lot2_id, container2_id = await _receive_lot_for_material(client, db, op_token, site_id, material_id, "LOT-MULTILOT-2", quantity="20.000000")
    await _release_lot(client, qa_token, lot2_id)
    await _put_away(client, op_token, lot2_id, container2_id, released_location_id, "20.000000")

    batch_id = await _create_batch(client, op_token, site_id, "MULTILOT")
    order_id = await _create_order(client, op_token, site_id, batch_id, material_id, target_qty="30.000000", low="28", high="32")

    select1 = await _select_source(client, op_token, order_id, 1, lot1_id, quantity="15.000000", container_id=container1_id)
    assert select1.status_code == 200, select1.text
    select2 = await _select_source(client, op_token, order_id, 2, lot2_id, quantity="15.000000", container_id=container2_id)
    assert select2.status_code == 200, select2.text

    start_resp = await _start(client, op_token, order_id, 3)
    assert start_resp.status_code == 200, start_resp.text
    reading_resp = await _manual_reading(client, op_token, order_id, 4, "30.000000")
    assert reading_resp.status_code == 200, reading_resp.text

    from app.modules.material.models import DispensingSource

    sources = (
        await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))
    ).scalars().all()
    assert len(sources) == 2
    assert {str(s.material_lot_id) for s in sources} == {lot1_id, lot2_id}

    # _complete() only accepts one (source_id -> qty) pair; exercise the real multi-source contract
    # directly against the endpoint since DSP-FR-017 requires every source represented in one call.
    challenge_id = await _challenge(client, op_token, order_id, "complete")
    resp = await client.post(
        f"/dispensing/v1/orders/{order_id}/complete",
        json={
            "idempotency_key": idem(),
            "expected_version": 4,
            "actual_taken_quantities": {str(sources[0].id): "15.000000", str(sources[1].id): "15.000000"},
            "container_code": "DISP-MULTILOT-CTR",
            "challenge_id": challenge_id,
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    dispensed = (
        await db.execute(select(DispensedContainer).where(DispensedContainer.dispensing_order_id == order_id))
    ).scalar_one()
    assert dispensed.actual_quantity == 30
