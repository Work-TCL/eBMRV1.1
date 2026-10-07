"""Materials & QC thin slice: receipt (auto-quarantine) -> release (signed) -> dispense -> consume into a
batch (MAT-013 eligibility). Mirrors the negative-case discipline used for the batch kernel.

2026-09-22: the old direct `issue_material_to_batch` path (`POST /batches/{id}/material-issues`) this
file used to exercise was retired -- it was never called by any frontend page, had no permission check at
all, and duplicated `RecordConsumption` (via Dispensing) with a second, disconnected
`MaterialLot.available_quantity` writer. MAT-013 eligibility and over-quantity rejection are now proven
against the real dispensing flow instead (`select_dispensing_source`/`complete_dispensing`)."""

from tests.conftest import auth_headers, idem, login
from tests.test_dispensing_flow import _create_batch_with_requirement, _create_order, _select_source
from tests.test_inventory_flow import _put_away, _receive_and_examine


async def _create_material(client, site_id, code="RM-1", name="Raw Material 1", uom="kg"):
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


async def _receive_lot(client, token, material_id, site_id, internal_lot="LOT-1", quantity="100.000000"):
    resp = await client.post(
        f"/materials/{material_id}/lots",
        json={
            "idempotency_key": idem(),
            "material_id": material_id,
            "site_id": str(site_id),
            "internal_lot": internal_lot,
            "received_quantity": quantity,
            "uom": "kg",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _release_lot(client, token, lot_id):
    """SG-075 (2026-09-22): material_lot release/reject is now the only disposition path (QA Releaser,
    Document 106 rows 44/45) -- the legacy QC-Reviewer-signed `/disposition` endpoint was retired."""
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
            "expected_version": 1,
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_create_material_without_code_auto_generates(client, seeded):
    pe_token = await login(client, "process.engineer")
    site_id = seeded["site_id"]

    resp1 = await client.post(
        "/materials",
        json={"idempotency_key": idem(), "site_id": str(site_id), "name": "Auto Coded Material", "uom": "kg"},
        headers=auth_headers(pe_token),
    )
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post(
        "/materials",
        json={"idempotency_key": idem(), "site_id": str(site_id), "name": "Auto Coded Material 2", "uom": "kg"},
        headers=auth_headers(pe_token),
    )
    assert resp2.status_code == 200, resp2.text

    listing = (await client.get("/materials", headers=auth_headers(pe_token))).json()
    codes = {item["id"]: item["code"] for item in listing["items"]}
    code1 = codes[resp1.json()["aggregate_id"]]
    code2 = codes[resp2.json()["aggregate_id"]]
    assert code1.startswith("MAT-")
    assert code2.startswith("MAT-")
    assert code1 != code2


async def test_receipt_enters_quarantine(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id)
    lot_id = await _receive_lot(client, op_token, material_id, site_id)

    detail = (await client.get(f"/material-lots/{lot_id}", headers=auth_headers(op_token))).json()
    assert detail["status"] == "quarantine"
    assert detail["available_quantity"] == "100.000000"


async def test_receive_lot_creates_a_container(client, seeded):
    # Bug fix: receive_material_lot() (the "Receive lot" quick-create shortcut) previously created a lot
    # with zero MaterialContainer rows, silently blocking Transfer/Split/Sampling Order downstream (they
    # all require at least one container). Mirrors the single-container case of examine_receipt()'s own
    # container-creation loop.
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id)
    lot_id = await _receive_lot(client, op_token, material_id, site_id, quantity="42.000000")

    resp = await client.get(f"/material-lots/{lot_id}/containers", headers=auth_headers(op_token))
    assert resp.status_code == 200, resp.text
    containers = resp.json()["items"]
    assert len(containers) == 1
    assert containers[0]["received_quantity"] == "42.000000"
    assert containers[0]["current_quantity"] == "42.000000"
    assert containers[0]["version"] == 1


async def test_receive_lot_requires_material_receipt_create_permission(client, seeded):
    """2026-09-19, docs/testing/demo-gujarati/03 gap: this legacy direct-lot-creation endpoint had no
    evaluate_policy() call at all -- any authenticated user, any role, could receive a lot. Now reuses
    `material_receipt.create`, the same permission the real Document 19 receipt flow gates."""
    qc_token = await login(client, "qc.reviewer")  # holds no material_receipt.create
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id)
    resp = await client.post(
        f"/materials/{material_id}/lots",
        json={
            "idempotency_key": idem(),
            "material_id": material_id,
            "site_id": str(site_id),
            "internal_lot": "LOT-RBAC-1",
            "received_quantity": "10.000000",
            "uom": "kg",
        },
        headers=auth_headers(qc_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_release_requires_qa_releaser_role(client, seeded):
    """SG-075: material_lot release is QA Releaser-signed (Document 106 row 44) -- an Operator holds
    neither the RBAC permission nor the signature-policy role."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id)
    lot_id = await _receive_lot(client, op_token, material_id, site_id)

    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(op_token),
        )
    ).json()
    resp = await client.post(
        f"/materials/v1/lots/{lot_id}/release",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_issue_from_quarantine_lot_rejected(client, db, seeded):
    """MAT-013: only a released lot is eligible to be selected as a dispensing source -- put away in the
    quarantine zone first, so the rejection is genuinely about lot status, not an empty ledger balance."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    quarantine_location_id = str(seeded["locations"]["QUARANTINE-01"].id)
    material_id, lot_id, containers = await _receive_and_examine(client, db, op_token, site_id, "RM-MAT1", "LOT-MAT1")
    await _put_away(client, op_token, lot_id, containers[0], quarantine_location_id, "100.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(
        client, op_token, site_id, "MAT1", material_id, target_qty="5.000000", low="1.000000", high="10.000000"
    )
    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)

    resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=containers[0], quantity="5.000000")
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "LOT_INELIGIBLE"


async def test_full_material_genealogy_flow(client, seeded, db):
    """Receive -> release -> put-away -> dispense -> consume into a batch, then prove: (1) the real
    consumption path decrements the lot's `available_quantity` (2026-09-22 fix -- `complete_dispensing`
    used to only touch `InventoryBalanceProjection`, leaving the Material Lots page permanently stale),
    and (2) `record_consumption` now writes the MAT-021 genealogy edge `issue_material_to_batch` used to
    own before it was retired."""
    import uuid as uuid_mod

    from sqlalchemy import select

    from app.modules.genealogy.models import GenealogyEdge, GenealogyNode
    from app.modules.material.models import DispensedContainer, DispensingSource, MaterialConsumption
    from tests.test_dispensing_flow import _complete, _manual_reading, _start, _verify

    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    releaser_token = await login(client, "qa.releaser")  # SG-075: release is QA Releaser-signed
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "RM-MAT2", "LOT-MAT2", quantity="50.000000"
    )
    await _release_lot(client, releaser_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "50.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(
        client, op_token, site_id, "MAT2", material_id, target_qty="12.500000", low="12.000000", high="13.000000"
    )

    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    select_resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=containers[0], quantity="12.500000")
    assert select_resp.status_code == 200, select_resp.text
    assert (await _start(client, op_token, order_id, 2)).status_code == 200
    assert (await _manual_reading(client, op_token, order_id, 3, "12.500000")).status_code == 200
    assert (await _verify(client, qc_token, order_id, 3)).status_code == 200

    src = (await db.execute(select(DispensingSource).where(DispensingSource.dispensing_order_id == order_id))).scalar_one()
    complete_resp = await _complete(client, op_token, order_id, 4, str(src.id), "12.500000", "DC-MAT2")
    assert complete_resp.status_code == 200, complete_resp.text

    lot_detail = (await client.get(f"/material-lots/{lot_id}", headers=auth_headers(op_token))).json()
    assert lot_detail["available_quantity"] == "37.500000"
    assert lot_detail["status"] == "released"

    dispensed = (
        await db.execute(select(DispensedContainer).where(DispensedContainer.dispensing_order_id == order_id))
    ).scalar_one()
    dispensed_container_id = str(dispensed.id)
    consume_resp = await client.post(
        "/materials/v1/consumptions",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "dispensed_container_id": dispensed_container_id,
            "quantity": "12.500000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    assert consume_resp.status_code == 200, consume_resp.text

    rows = (await db.execute(select(MaterialConsumption).where(MaterialConsumption.batch_id == uuid_mod.UUID(batch_id)))).scalars().all()
    assert len(rows) == 1
    assert rows[0].uom == "kg"
    assert rows[0].uom_id is not None

    lot_node = (
        await db.execute(
            select(GenealogyNode).where(
                GenealogyNode.authoritative_record_type == "material_lot",
                GenealogyNode.authoritative_record_id == uuid_mod.UUID(lot_id),
            )
        )
    ).scalar_one()
    batch_node = (
        await db.execute(
            select(GenealogyNode).where(
                GenealogyNode.authoritative_record_type == "batch",
                GenealogyNode.authoritative_record_id == uuid_mod.UUID(batch_id),
            )
        )
    ).scalar_one()
    assert lot_node.node_type == "material_lot"
    assert batch_node.node_type == "drug_batch"
    edge = (
        await db.execute(
            select(GenealogyEdge).where(
                GenealogyEdge.from_node_id == lot_node.id, GenealogyEdge.to_node_id == batch_node.id,
                GenealogyEdge.edge_type == "CONSUMED_IN",
            )
        )
    ).scalar_one()
    assert edge.quantity == rows[0].quantity

    # Real read-path proof too: GET /genealogy/v1/nodes/{id}/ancestors from the batch node finds the lot.
    ancestors = (
        await client.get(f"/genealogy/v1/nodes/{batch_node.id}/ancestors", headers=auth_headers(op_token))
    ).json()
    assert str(lot_node.id) in {n["node_id"] for n in ancestors["nodes"]}


async def test_over_dispense_source_selection_rejected(client, db, seeded):
    """MAT-013 over-issue guard, proven at the real point it's enforced: selecting more than a lot's
    put-away balance as a dispensing source (`select_dispensing_source`'s own `SourceQuantityInsufficientError`)."""
    op_token = await login(client, "operator1")
    releaser_token = await login(client, "qa.releaser")  # SG-075: release is QA Releaser-signed
    site_id = seeded["site_id"]
    released_location_id = str(seeded["locations"]["RELEASED-01"].id)

    material_id, lot_id, containers = await _receive_and_examine(
        client, db, op_token, site_id, "RM-OVER", "LOT-OVER", quantity="10.000000"
    )
    await _release_lot(client, releaser_token, lot_id)
    await _put_away(client, op_token, lot_id, containers[0], released_location_id, "10.000000")
    batch_id, batch_step_id = await _create_batch_with_requirement(
        client, op_token, site_id, "OVER", material_id, target_qty="10.000000", low="1.000000", high="999.000000"
    )

    order_id = await _create_order(client, op_token, site_id, batch_id, batch_step_id, material_id)
    resp = await _select_source(client, op_token, order_id, 1, lot_id, container_id=containers[0], quantity="999.000000")
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "SOURCE_QUANTITY_INSUFFICIENT"
