"""Materials & QC thin slice: receipt (auto-quarantine) -> QC disposition (signed) -> issue to a
batch (MAT-013 eligibility). Mirrors the negative-case discipline used for the batch kernel."""

from tests.conftest import auth_headers, idem, login


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
    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "disposition"},
            headers=auth_headers(token),
        )
    ).json()
    resp = await client.post(
        f"/material-lots/{lot_id}/disposition",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "decision": "released",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def test_receipt_enters_quarantine(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id)
    lot_id = await _receive_lot(client, op_token, material_id, site_id)

    detail = (await client.get(f"/material-lots/{lot_id}")).json()
    assert detail["status"] == "quarantine"
    assert detail["available_quantity"] == "100.000000"


async def test_disposition_requires_qc_reviewer_role(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id)
    lot_id = await _receive_lot(client, op_token, material_id, site_id)

    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "disposition"},
            headers=auth_headers(op_token),
        )
    ).json()
    resp = await client.post(
        f"/material-lots/{lot_id}/disposition",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "decision": "released",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_issue_from_quarantine_lot_rejected(client, seeded):
    """MAT-013: only a released lot is eligible for issue."""
    from tests.test_inventory_flow import _create_batch

    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id)
    lot_id = await _receive_lot(client, op_token, material_id, site_id)

    # SG-173 / ADR-0013: material-issue resolves the batch from `ebmr.gxp_batch`.
    batch_id = await _create_batch(client, op_token, site_id, "MAT1")

    resp = await client.post(
        f"/batches/{batch_id}/material-issues",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "batch_id": batch_id,
            "quantity": "5.000000",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_full_material_genealogy_flow(client, seeded, db):
    from sqlalchemy import select
    from app.modules.material.models import MaterialIssue
    from tests.test_inventory_flow import _create_batch

    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]

    material_id = await _create_material(client, site_id)
    lot_id = await _receive_lot(client, op_token, material_id, site_id, quantity="50.000000")
    await _release_lot(client, qc_token, lot_id)

    # SG-173 / ADR-0013: the material-issue command resolves the batch from `ebmr.gxp_batch`, so the
    # batch must be created there (not the retired `ebmr.batches` scaffold via POST /batches).
    batch_id = await _create_batch(client, op_token, site_id, "MAT2")

    resp = await client.post(
        f"/batches/{batch_id}/material-issues",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 2,  # v1 receipt -> v2 after release
            "batch_id": batch_id,
            "quantity": "12.500000",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    lot_detail = (await client.get(f"/material-lots/{lot_id}")).json()
    assert lot_detail["available_quantity"] == "37.500000"
    assert lot_detail["status"] == "released"

    issues = (await client.get(f"/batches/{batch_id}/material-issues")).json()
    assert len(issues) == 1
    assert issues[0]["internal_lot"] == "LOT-1"
    assert issues[0]["quantity"] == "12.500000"

    rows = (await db.execute(select(MaterialIssue).where(MaterialIssue.batch_id == batch_id))).scalars().all()
    assert len(rows) == 1
    # SG-146 (remainder): "kg" has no released rules.gxp_uom row in this environment -- the dual-write
    # is a no-op, and the issue's uom_id is copied from the lot's own (also unresolved) value.
    assert rows[0].uom == "kg"
    assert rows[0].uom_id is None


async def test_over_issue_rejected(client, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]

    material_id = await _create_material(client, site_id, code="RM-OVER")
    lot_id = await _receive_lot(client, op_token, material_id, site_id, internal_lot="LOT-OVER", quantity="10.000000")
    await _release_lot(client, qc_token, lot_id)

    # SG-173 / ADR-0013: material-issue resolves the batch from `ebmr.gxp_batch`.
    from tests.test_inventory_flow import _create_batch

    batch_id = await _create_batch(client, op_token, site_id, "OVER")

    resp = await client.post(
        f"/batches/{batch_id}/material-issues",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 2,
            "batch_id": batch_id,
            "quantity": "999.000000",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"
