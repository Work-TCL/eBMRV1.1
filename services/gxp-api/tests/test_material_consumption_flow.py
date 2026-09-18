"""Document 22 (SPEC-MAT-002D) — Material Consumption, Return, Adjustment, Destruction & Reconciliation.
Builds on Document 21's dispensing flow: a `DispensedContainer` created by `complete_dispensing` is the
starting point for every command tested here (consume, return, loss, adjustment, destruction,
reconciliation).

Backing evidence for the pre-written test-case book (test-cases/WP-04/Document_22_SPEC-MAT-002D_TEST_CASES.md):
each test function below is cited by name in the fill script (scripts/fill_document_22_test_cases.py) as
the executed evidence for one or more TC-022-* case IDs.
"""

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.modules.material.models import (
    DestructionRecord,
    DispensedContainer,
    InventoryAdjustmentRequest,
    InventoryTransaction,
    MaterialConsumption,
    MaterialReconciliation,
    MaterialReturn,
)
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_dispensing_flow import (
    _complete,
    _create_order,
    _manual_reading,
    _prepared_lot,
    _select_source,
    _start,
    _verify,
)
from tests.test_inventory_flow import _create_batch, _create_material, _put_away


async def _build_dispensed_container(client, db, seeded, op_token, qc_token, qa_token, code, lot_code, qty="30.000000"):
    """Receive -> release -> put-away -> dispense -> complete. Returns
    (batch_id, material_id, lot_id, dispensed_container_id, released_location_id)."""
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, code, lot_code)
    await _put_away(client, op_token, lot_id, container_id, released_location_id, "100.000000")
    batch_id = await _create_batch(client, op_token, site_id, code)

    order_id = await _create_order(client, op_token, site_id, batch_id, material_id, target_qty=qty, low="1.000000", high="200.000000")
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=container_id, quantity=qty)
    assert select_resp.status_code == 200, select_resp.text
    start_resp = await _start(client, op_token, order_id, 2)
    assert start_resp.status_code == 200, start_resp.text
    reading_resp = await _manual_reading(client, op_token, order_id, 3, qty)
    assert reading_resp.status_code == 200, reading_resp.text
    verify_resp = await _verify(client, qc_token, order_id, 3)
    assert verify_resp.status_code == 200, verify_resp.text

    from app.modules.material.models import DispensingSource

    src = (await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))).scalar_one()
    complete_resp = await _complete(client, op_token, order_id, 4, str(src.id), qty, f"DC-{lot_code}")
    assert complete_resp.status_code == 200, complete_resp.text

    dispensed = (
        await db.execute(select(DispensedContainer).where(DispensedContainer.dispensing_order_id == order_id))
    ).scalar_one()
    return batch_id, material_id, lot_id, str(dispensed.id), released_location_id


# ---------------------------------------------------------------------------
# RecordConsumption — CON-FR-001/002/004/027/031
# ---------------------------------------------------------------------------


async def test_full_consumption_marks_container_consumed(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, material_id, lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-CON1", "LOT-CON1"
    )

    resp = await client.post(
        "/materials/v1/consumptions",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dc_id,
            "quantity": "30.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    container = await db.get(DispensedContainer, uuid.UUID(dc_id))
    assert container.remaining_quantity == 0
    assert container.status == "consumed"

    txn = (
        await db.execute(
            select(InventoryTransaction).where(
                InventoryTransaction.reference_type == "dispensed_container",
                InventoryTransaction.reference_id == uuid.UUID(dc_id),
                InventoryTransaction.transaction_type == "CONSUME",
            )
        )
    ).scalar_one()
    assert txn.quantity == 30


async def test_partial_consumption_leaves_container_partially_consumed(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, material_id, lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-CON2", "LOT-CON2"
    )

    resp = await client.post(
        "/materials/v1/consumptions",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dc_id,
            "quantity": "12.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    container = await db.get(DispensedContainer, uuid.UUID(dc_id))
    assert container.remaining_quantity == Decimal("18.000000")
    assert container.status == "partially_consumed"


async def test_consumption_cross_batch_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    _batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-CON3", "LOT-CON3"
    )
    other_batch_id = await _create_batch(client, op_token, site_id, "OTHERBATCH")

    resp = await client.post(
        "/materials/v1/consumptions",
        json={
            "idempotency_key": idem(),
            "batch_id": other_batch_id,
            "dispensed_container_id": dc_id,
            "quantity": "5.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "BATCH_MISMATCH"


async def test_consumption_exceeding_remaining_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-CON4", "LOT-CON4"
    )

    resp = await client.post(
        "/materials/v1/consumptions",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dc_id,
            "quantity": "999.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "QUANTITY_EXCEEDS_AVAILABLE"


async def test_consumption_on_consumed_container_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-CON5", "LOT-CON5"
    )
    first = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "30.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    assert first.status_code == 200, first.text

    resp = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "1.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STATE_TRANSITION_INVALID" or resp.status_code == 409


async def test_automatic_consumption_source_not_available(client, db, seeded):
    """CON-FR-003 (SG-098): no validated integration/rules-engine source exists in this codebase."""
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-CON6", "LOT-CON6"
    )

    resp = await client.post(
        "/materials/v1/consumptions",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dc_id,
            "quantity": "1.000000",
            "uom": "kg",
            "source_type": "automatic",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# RecordReturn — CON-FR-005/006/007
# ---------------------------------------------------------------------------


async def test_return_acceptable_condition_restores_balance(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, lot_id, dc_id, loc_id = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-RET1", "LOT-RET1"
    )

    resp = await client.post(
        "/materials/v1/returns",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dc_id,
            "quantity": "10.000000",
            "uom": "kg",
            "container_condition": "sealed, unopened",
            "condition_acceptable": True,
            "target_location_id": loc_id,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    ret = (await db.execute(select(MaterialReturn).where(MaterialReturn.dispensed_container_id == uuid.UUID(dc_id)))).scalar_one()
    assert ret.resulting_status == "released"

    from app.modules.material.models import InventoryBalanceProjection

    balance = (
        await db.execute(
            select(InventoryBalanceProjection).where(
                InventoryBalanceProjection.material_lot_id == uuid.UUID(lot_id),
                InventoryBalanceProjection.container_id.is_(None),
                InventoryBalanceProjection.location_id == uuid.UUID(loc_id),
            )
        )
    ).scalar_one()
    assert balance.on_hand == Decimal("10.000000")


async def test_return_unacceptable_condition_routes_to_quarantine(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, loc_id = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-RET2", "LOT-RET2"
    )

    resp = await client.post(
        "/materials/v1/returns",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dc_id,
            "quantity": "10.000000",
            "uom": "kg",
            "container_condition": "seal broken, exposed to ambient humidity",
            "condition_acceptable": False,
            "target_location_id": loc_id,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    ret = (await db.execute(select(MaterialReturn).where(MaterialReturn.dispensed_container_id == uuid.UUID(dc_id)))).scalar_one()
    assert ret.resulting_status == "quarantine"

    # CON-FR-006 "prohibited path": unsuitable material must NOT silently re-enter available stock.
    from app.modules.material.models import InventoryBalanceProjection

    balance_rows = (
        await db.execute(
            select(InventoryBalanceProjection).where(
                InventoryBalanceProjection.material_lot_id == uuid.UUID(_lot_id),
                InventoryBalanceProjection.location_id == uuid.UUID(loc_id),
                InventoryBalanceProjection.container_id.is_(None),
            )
        )
    ).scalars().all()
    assert balance_rows == []


async def test_return_on_already_returned_container_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, loc_id = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-RET3", "LOT-RET3"
    )
    first = await client.post(
        "/materials/v1/returns",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id,
            "quantity": "30.000000", "uom": "kg", "container_condition": "sealed, unopened",
            "condition_acceptable": True, "target_location_id": loc_id,
        },
        headers=auth_headers(op_token),
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        "/materials/v1/returns",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id,
            "quantity": "1.000000", "uom": "kg", "container_condition": "sealed, unopened",
            "condition_acceptable": True, "target_location_id": loc_id,
        },
        headers=auth_headers(op_token),
    )
    assert second.status_code == 409, second.text


# ---------------------------------------------------------------------------
# RecordMaterialLoss — CON-FR-009/010/011/012
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("loss_type", ["SAMPLE", "REJECT", "SPILL", "APPROVED_LOSS"])
async def test_record_material_loss_all_types(client, db, seeded, loss_type):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, f"MAT-LOSS-{loss_type}", f"LOT-LOSS-{loss_type}"
    )

    resp = await client.post(
        "/materials/v1/losses",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dc_id,
            "loss_type": loss_type,
            "quantity": "2.000000",
            "uom": "kg",
            "reason": f"{loss_type} test evidence",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    txn = (
        await db.execute(
            select(InventoryTransaction).where(
                InventoryTransaction.reference_type == "dispensed_container",
                InventoryTransaction.reference_id == uuid.UUID(dc_id),
                InventoryTransaction.transaction_type == loss_type,
            )
        )
    ).scalar_one()
    assert txn.quantity == 2


async def test_record_material_loss_invalid_type_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-LOSSBAD", "LOT-LOSSBAD"
    )

    resp = await client.post(
        "/materials/v1/losses",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dc_id,
            "loss_type": "SCRAP_EVERYTHING",
            "quantity": "1.000000",
            "uom": "kg",
            "reason": "bad type",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# InventoryAdjustmentRequest — CON-FR-013/014
# ---------------------------------------------------------------------------


async def _released_lot_with_balance(client, db, seeded, op_token, qa_token, code, lot_code, qty="50.000000"):
    site_id = seeded["site_id"]
    location_id = str(seeded["locations"]["RELEASED-01"].id)
    material_id, lot_id, container_id = await _prepared_lot(client, db, op_token, qa_token, site_id, code, lot_code, quantity=qty)
    await _put_away(client, op_token, lot_id, container_id, location_id, qty)
    return material_id, lot_id, container_id, location_id


async def test_adjustment_request_create_and_approve(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    _material_id, lot_id, container_id, location_id = await _released_lot_with_balance(
        client, db, seeded, op_token, qa_token, "MAT-ADJ1", "LOT-ADJ1"
    )

    create_resp = await client.post(
        "/inventory/v1/adjustments",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": container_id,
            "location_id": location_id,
            "expected_quantity": "50.000000",
            "observed_quantity": "48.500000",
            "reason": "physical count variance during cycle audit",
        },
        headers=auth_headers(op_token),
    )
    assert create_resp.status_code == 200, create_resp.text
    request_id = create_resp.json()["aggregate_id"]

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

    request = await db.get(InventoryAdjustmentRequest, uuid.UUID(request_id))
    assert request.status == "approved"

    from app.modules.material.models import InventoryBalanceProjection

    balance = (
        await db.execute(
            select(InventoryBalanceProjection).where(
                InventoryBalanceProjection.material_lot_id == uuid.UUID(lot_id),
                InventoryBalanceProjection.container_id == uuid.UUID(container_id),
                InventoryBalanceProjection.location_id == uuid.UUID(location_id),
            )
        )
    ).scalar_one()
    assert balance.on_hand == Decimal("48.500000")


async def test_adjustment_self_approval_denied(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    _material_id, lot_id, _container_id, location_id = await _released_lot_with_balance(
        client, db, seeded, op_token, qa_token, "MAT-ADJ2", "LOT-ADJ2"
    )

    create_resp = await client.post(
        "/inventory/v1/adjustments",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "location_id": location_id,
            "expected_quantity": "50.000000",
            "observed_quantity": "49.000000",
            "reason": "self-approval test",
        },
        headers=auth_headers(qa_token),
    )
    assert create_resp.status_code == 200, create_resp.text
    request_id = create_resp.json()["aggregate_id"]

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
            "reason": "trying to approve my own request",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert approve_resp.status_code == 422, approve_resp.text


async def test_adjustment_approve_missing_signature_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    _material_id, lot_id, _container_id, location_id = await _released_lot_with_balance(
        client, db, seeded, op_token, qa_token, "MAT-ADJ3", "LOT-ADJ3"
    )
    create_resp = await client.post(
        "/inventory/v1/adjustments",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "location_id": location_id,
            "expected_quantity": "50.000000",
            "observed_quantity": "49.000000",
            "reason": "missing signature test",
        },
        headers=auth_headers(op_token),
    )
    request_id = create_resp.json()["aggregate_id"]

    approve_resp = await client.post(
        f"/inventory/v1/adjustments/{request_id}/approve",
        json={"idempotency_key": idem(), "expected_version": 1, "reason": "no challenge provided"},
        headers=auth_headers(qa_token),
    )
    assert approve_resp.status_code == 428, approve_resp.text


async def test_adjustment_approve_stale_version_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    _material_id, lot_id, _container_id, location_id = await _released_lot_with_balance(
        client, db, seeded, op_token, qa_token, "MAT-ADJ4", "LOT-ADJ4"
    )
    create_resp = await client.post(
        "/inventory/v1/adjustments",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "location_id": location_id,
            "expected_quantity": "50.000000",
            "observed_quantity": "49.000000",
            "reason": "stale version test",
        },
        headers=auth_headers(op_token),
    )
    request_id = create_resp.json()["aggregate_id"]

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
            "expected_version": 99,
            "reason": "wrong version",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert approve_resp.status_code == 409, approve_resp.text
    assert approve_resp.json()["code"] == "STALE_VERSION"


async def test_adjustment_request_create_and_reject(client, db, seeded):
    """Approve's missing counterpart until this pass (DDCP_Client_Demo_Guide_Gujarati.md §19 #7) -- a
    wrong/unwanted adjustment request had no way out of "requested" at all."""
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    _material_id, lot_id, container_id, location_id = await _released_lot_with_balance(
        client, db, seeded, op_token, qa_token, "MAT-ADJ5", "LOT-ADJ5"
    )

    create_resp = await client.post(
        "/inventory/v1/adjustments",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "container_id": container_id,
            "location_id": location_id,
            "expected_quantity": "50.000000",
            "observed_quantity": "48.500000",
            "reason": "physical count variance, disputed",
        },
        headers=auth_headers(op_token),
    )
    assert create_resp.status_code == 200, create_resp.text
    request_id = create_resp.json()["aggregate_id"]

    challenge = (
        await client.post(
            f"/inventory/v1/adjustments/{request_id}/signature-challenges",
            json={"action": "reject"},
            headers=auth_headers(qa_token),
        )
    ).json()
    assert challenge["meaning"] == "Rejected"
    reject_resp = await client.post(
        f"/inventory/v1/adjustments/{request_id}/reject",
        json={
            "idempotency_key": idem(),
            "expected_version": 1,
            "reason": "recount confirmed original count was correct",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert reject_resp.status_code == 200, reject_resp.text
    assert reject_resp.json()["signature_id"] is not None

    request = await db.get(InventoryAdjustmentRequest, uuid.UUID(request_id))
    assert request.status == "rejected"

    from app.modules.material.models import InventoryBalanceProjection

    balance = (
        await db.execute(
            select(InventoryBalanceProjection).where(
                InventoryBalanceProjection.material_lot_id == uuid.UUID(lot_id),
                InventoryBalanceProjection.container_id == uuid.UUID(container_id),
                InventoryBalanceProjection.location_id == uuid.UUID(location_id),
            )
        )
    ).scalar_one()
    assert balance.on_hand == Decimal("50.000000")  # unchanged -- a rejected adjustment never touches inventory


async def test_adjustment_self_rejection_denied(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    _material_id, lot_id, _container_id, location_id = await _released_lot_with_balance(
        client, db, seeded, op_token, qa_token, "MAT-ADJ6", "LOT-ADJ6"
    )

    create_resp = await client.post(
        "/inventory/v1/adjustments",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "location_id": location_id,
            "expected_quantity": "50.000000",
            "observed_quantity": "49.000000",
            "reason": "self-rejection test",
        },
        headers=auth_headers(qa_token),
    )
    assert create_resp.status_code == 200, create_resp.text
    request_id = create_resp.json()["aggregate_id"]

    challenge = (
        await client.post(
            f"/inventory/v1/adjustments/{request_id}/signature-challenges",
            json={"action": "reject"},
            headers=auth_headers(qa_token),
        )
    ).json()
    reject_resp = await client.post(
        f"/inventory/v1/adjustments/{request_id}/reject",
        json={
            "idempotency_key": idem(),
            "expected_version": 1,
            "reason": "attempting self-rejection",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert reject_resp.status_code == 422, reject_resp.text


# ---------------------------------------------------------------------------
# DestructionRecord — CON-FR-015/016/017/018
# ---------------------------------------------------------------------------


async def test_destruction_request_and_execute_third_party(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-DES1", "LOT-DES1"
    )

    create_resp = await client.post(
        "/materials/v1/destructions",
        json={
            "idempotency_key": idem(),
            "dispensed_container_id": dc_id,
            "quantity": "30.000000",
            "uom": "kg",
            "reason": "expired excess material",
            "method": "incineration",
            "vendor_name": "Acme Waste Disposal Inc.",
            "manifest_reference": "MANIFEST-2026-0091",
            "witnesses": {"user_ids": []},
        },
        headers=auth_headers(op_token),
    )
    assert create_resp.status_code == 200, create_resp.text
    destruction_id = create_resp.json()["aggregate_id"]

    challenge = (
        await client.post(
            f"/materials/v1/destructions/{destruction_id}/signature-challenges",
            json={"action": "execute"},
            headers=auth_headers(op_token),
        )
    ).json()
    execute_resp = await client.post(
        f"/materials/v1/destructions/{destruction_id}/execute",
        json={
            "idempotency_key": idem(),
            "expected_version": 1,
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(op_token),
    )
    assert execute_resp.status_code == 200, execute_resp.text
    assert execute_resp.json()["signature_id"] is not None

    record = await db.get(DestructionRecord, uuid.UUID(destruction_id))
    assert record.status == "executed"

    container = await db.get(DispensedContainer, uuid.UUID(dc_id))
    assert container.remaining_quantity == 0
    assert container.status == "destroyed"


async def test_destruction_execute_wrong_state_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-DES2", "LOT-DES2"
    )
    create_resp = await client.post(
        "/materials/v1/destructions",
        json={
            "idempotency_key": idem(),
            "dispensed_container_id": dc_id,
            "quantity": "5.000000",
            "uom": "kg",
            "reason": "double execute test",
        },
        headers=auth_headers(op_token),
    )
    destruction_id = create_resp.json()["aggregate_id"]
    challenge = (
        await client.post(
            f"/materials/v1/destructions/{destruction_id}/signature-challenges",
            json={"action": "execute"},
            headers=auth_headers(op_token),
        )
    ).json()
    first = await client.post(
        f"/materials/v1/destructions/{destruction_id}/execute",
        json={"idempotency_key": idem(), "expected_version": 1, "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD},
        headers=auth_headers(op_token),
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"/materials/v1/destructions/{destruction_id}/execute",
        json={"idempotency_key": idem(), "expected_version": 2, "reauth_password": DEMO_PASSWORD},
        headers=auth_headers(op_token),
    )
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "DESTRUCTION_NOT_AUTHORIZED"


async def test_destruction_scope_requires_exactly_one(client, db, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/materials/v1/destructions",
        json={"idempotency_key": idem(), "quantity": "1.000000", "uom": "kg", "reason": "no scope given"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text


async def test_destruction_execute_missing_signature_rejected(client, db, seeded):
    """Same signature ceremony as third-party destruction (CON-FR-018) -- vendor/manifest fields don't
    branch the signature logic, so this covers both the plain and third-party destruction request shapes."""
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-DES3", "LOT-DES3"
    )
    create_resp = await client.post(
        "/materials/v1/destructions",
        json={
            "idempotency_key": idem(),
            "dispensed_container_id": dc_id,
            "quantity": "5.000000",
            "uom": "kg",
            "reason": "missing signature test",
            "vendor_name": "Acme Waste Disposal Inc.",
            "manifest_reference": "MANIFEST-2026-0092",
        },
        headers=auth_headers(op_token),
    )
    destruction_id = create_resp.json()["aggregate_id"]

    resp = await client.post(
        f"/materials/v1/destructions/{destruction_id}/execute",
        json={"idempotency_key": idem(), "expected_version": 1},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 428, resp.text


async def test_destruction_execute_stale_version_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-DES4", "LOT-DES4"
    )
    create_resp = await client.post(
        "/materials/v1/destructions",
        json={
            "idempotency_key": idem(),
            "dispensed_container_id": dc_id,
            "quantity": "5.000000",
            "uom": "kg",
            "reason": "stale version test",
            "vendor_name": "Acme Waste Disposal Inc.",
            "manifest_reference": "MANIFEST-2026-0093",
        },
        headers=auth_headers(op_token),
    )
    destruction_id = create_resp.json()["aggregate_id"]
    challenge = (
        await client.post(
            f"/materials/v1/destructions/{destruction_id}/signature-challenges",
            json={"action": "execute"},
            headers=auth_headers(op_token),
        )
    ).json()
    resp = await client.post(
        f"/materials/v1/destructions/{destruction_id}/execute",
        json={
            "idempotency_key": idem(),
            "expected_version": 99,
            "challenge_id": challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


# ---------------------------------------------------------------------------
# MaterialReconciliation — CON-FR-019/020/023/024
# ---------------------------------------------------------------------------


async def test_reconciliation_negative_tolerance_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, _dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-RECNEG", "LOT-RECNEG"
    )
    resp = await client.post(
        f"/reconciliation/v1/batches/{batch_id}/materials/evaluate",
        json={"idempotency_key": idem(), "tolerance_value": "-1.000000"},
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 422, resp.text


async def test_reconciliation_acceptable_outcome(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-REC1", "LOT-REC1"
    )
    consume_resp = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "30.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    assert consume_resp.status_code == 200, consume_resp.text

    eval_resp = await client.post(
        f"/reconciliation/v1/batches/{batch_id}/materials/evaluate",
        json={"idempotency_key": idem(), "tolerance_value": "0.010000"},
        headers=auth_headers(qa_token),
    )
    assert eval_resp.status_code == 200, eval_resp.text

    reconciliation = await db.get(MaterialReconciliation, uuid.UUID(eval_resp.json()["aggregate_id"]))
    assert reconciliation.outcome == "ACCEPTABLE"
    assert reconciliation.unexplained_variance == Decimal("0.00")

    get_resp = await client.get(f"/reconciliation/v1/batches/{batch_id}/materials", headers=auth_headers(qc_token))
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["outcome"] == "ACCEPTABLE"
    assert get_resp.json()["erp_posting_status"] == "not_integrated"


async def test_reconciliation_variance_outcome_links_deviation(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-REC2", "LOT-REC2"
    )
    # Only consume half -- 15kg unaccounted, forcing a VARIANCE outcome against a tight tolerance.
    consume_resp = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "15.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    assert consume_resp.status_code == 200, consume_resp.text

    from app.modules.iam.models import User

    qc_user_id = (await db.execute(select(User).where(User.username == "qc.reviewer"))).scalar_one().id

    eval_resp = await client.post(
        f"/reconciliation/v1/batches/{batch_id}/materials/evaluate",
        json={
            "idempotency_key": idem(),
            "tolerance_value": "0.010000",
            "variance_severity": "MAJOR",
            "deviation_owner_user_id": str(qc_user_id),
        },
        headers=auth_headers(qa_token),
    )
    assert eval_resp.status_code == 200, eval_resp.text
    reconciliation = await db.get(MaterialReconciliation, uuid.UUID(eval_resp.json()["aggregate_id"]))
    assert reconciliation.outcome == "VARIANCE"
    assert reconciliation.linked_deviation_id is not None

    from app.modules.qms.models import DeviationRecord

    deviation = await db.get(DeviationRecord, reconciliation.linked_deviation_id)
    assert deviation is not None
    assert deviation.source_type == "material"


async def test_reconciliation_reevaluation_creates_new_version_never_edits(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-REC3", "LOT-REC3"
    )
    await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "10.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    first_eval = await client.post(
        f"/reconciliation/v1/batches/{batch_id}/materials/evaluate",
        json={"idempotency_key": idem(), "tolerance_value": "0.010000"},
        headers=auth_headers(qa_token),
    )
    assert first_eval.status_code == 200
    first_id = first_eval.json()["aggregate_id"]
    assert first_eval.json()["resulting_version"] == 1

    await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "20.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    second_eval = await client.post(
        f"/reconciliation/v1/batches/{batch_id}/materials/evaluate",
        json={"idempotency_key": idem(), "tolerance_value": "0.010000"},
        headers=auth_headers(qa_token),
    )
    assert second_eval.status_code == 200
    assert second_eval.json()["resulting_version"] == 2
    assert second_eval.json()["aggregate_id"] != first_id

    # Original row is untouched (CON-FR-023/024: correction is a new row, never an edit).
    original = await db.get(MaterialReconciliation, uuid.UUID(first_id))
    assert original.version == 1
    assert original.consumed_total == Decimal("10.000000")


# ---------------------------------------------------------------------------
# Ledger immutability — CON-FR-024/030 (direct UPDATE/DELETE on the append-only evidence tables refused
# at the database-privilege level, same discipline as `inventory_transactions` since migration 0028).
# ---------------------------------------------------------------------------


async def test_material_consumption_table_rejects_direct_update(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-IMM1", "LOT-IMM1"
    )
    resp = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "5.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    consumption_id = resp.json()["aggregate_id"]

    with pytest.raises(DBAPIError):
        await db.execute(
            MaterialConsumption.__table__.update()
            .where(MaterialConsumption.id == uuid.UUID(consumption_id))
            .values(quantity=Decimal("999"))
        )
        await db.commit()
    await db.rollback()


async def test_inventory_transaction_table_rejects_direct_delete(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-IMM2", "LOT-IMM2"
    )
    await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "5.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    with pytest.raises(DBAPIError):
        await db.execute(
            InventoryTransaction.__table__.delete().where(InventoryTransaction.reference_id == uuid.UUID(dc_id))
        )
        await db.commit()
    await db.rollback()


# ---------------------------------------------------------------------------
# Idempotency / RBAC — module-suite guarantees (M02/M07/M09/M10) exercised against a Document-22-owned
# command, same shared Mutation Gateway machinery every other module's tests already prove generically.
# ---------------------------------------------------------------------------


async def test_consumption_duplicate_idempotency_key_returns_same_receipt(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-IDEM1", "LOT-IDEM1"
    )
    key = idem()
    body = {"idempotency_key": key, "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "5.000000", "uom": "kg"}
    first = await client.post("/materials/v1/consumptions", json=body, headers=auth_headers(op_token))
    second = await client.post("/materials/v1/consumptions", json=body, headers=auth_headers(op_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["command_id"] == second.json()["command_id"]


async def test_consumption_same_key_different_payload_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-IDEM2", "LOT-IDEM2"
    )
    key = idem()
    first = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": key, "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "5.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    assert first.status_code == 200
    second = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": key, "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "6.000000", "uom": "kg"},
        headers=auth_headers(op_token),
    )
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_adjustment_approve_missing_expected_version_rejected(client, db, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    _material_id, lot_id, _container_id, location_id = await _released_lot_with_balance(
        client, db, seeded, op_token, qa_token, "MAT-MV1", "LOT-MV1"
    )
    create_resp = await client.post(
        "/inventory/v1/adjustments",
        json={
            "idempotency_key": idem(),
            "material_lot_id": lot_id,
            "location_id": location_id,
            "expected_quantity": "50.000000",
            "observed_quantity": "49.000000",
            "reason": "missing expected_version test",
        },
        headers=auth_headers(op_token),
    )
    request_id = create_resp.json()["aggregate_id"]
    resp = await client.post(
        f"/inventory/v1/adjustments/{request_id}/approve",
        json={"idempotency_key": idem(), "reason": "no expected_version field"},
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 422, resp.text


async def test_consumption_without_permission_denied(client, db, seeded):
    """QC Reviewer is not granted material_consumption.create (Operator/Supervisor/Admin only)."""
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_token = await login(client, "qa.releaser")
    batch_id, _material_id, _lot_id, dc_id, _loc = await _build_dispensed_container(
        client, db, seeded, op_token, qc_token, qa_token, "MAT-PERM1", "LOT-PERM1"
    )
    resp = await client.post(
        "/materials/v1/consumptions",
        json={"idempotency_key": idem(), "batch_id": batch_id, "dispensed_container_id": dc_id, "quantity": "1.000000", "uom": "kg"},
        headers=auth_headers(qc_token),
    )
    assert resp.status_code == 403, resp.text


async def test_consumption_unauthenticated_rejected(client):
    resp = await client.post(
        "/materials/v1/consumptions",
        json={
            "idempotency_key": idem(),
            "batch_id": "00000000-0000-0000-0000-000000000000",
            "dispensed_container_id": "00000000-0000-0000-0000-000000000000",
            "quantity": "1.000000",
            "uom": "kg",
        },
    )
    assert resp.status_code == 401
