"""Document 19 (SPEC-MAT-002A) — Material Receipt, Quarantine & Quality Status. Extends the receipt ->
quarantine -> disposition thin slice in test_material_flow.py with the full RCV-FR-001..032 surface:
receipt -> examine (clean / discrepancy hold) -> sampling-order -> collect -> release/reject/retest ->
quality-status/release-readiness, plus the mandatory negative/security/concurrency set."""

import uuid

from tests.conftest import auth_headers, idem, login


async def _create_material(client, site_id, code="RM-D19", name="Raw Material D19", uom="kg"):
    # 2026-09-18: material.create is now Process Engineer/Admin-only (RBAC gap closure) -- this helper
    # always authors as process.engineer regardless of which actor the calling test is otherwise
    # exercising (receipt/examine/disposition remain that actor's own job).
    pe_token = await login(client, "process.engineer")
    resp = await client.post(
        "/materials",
        json={"idempotency_key": idem(), "site_id": str(site_id), "code": code, "name": name, "uom": uom},
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _create_receipt(
    client, token, site_id, material_id, receipt_number="RCPT-1", supplier_id=None, quantity="100.000000"
):
    resp = await client.post(
        "/materials/v1/receipts",
        json={
            "idempotency_key": idem(),
            "site_id": str(site_id),
            "receipt_number": receipt_number,
            "material_id": material_id,
            "supplier_id": supplier_id,
            "received_gross_quantity": quantity,
            "accepted_quantity": quantity,
            "uom": "kg",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _examine_clean(client, token, receipt_id, internal_lot="LOT-D19", container_count=2):
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
    return resp.json()


async def _lot_id_for_receipt(client, receipt_id) -> str:
    token = await login(client, "operator1")
    detail = (await client.get(f"/materials/v1/receipts/{receipt_id}", headers=auth_headers(token))).json()
    assert detail["state"] == "examined"
    lots = (await client.get("/material-lots", params={"page_size": 50}, headers=auth_headers(token))).json()["items"]
    matches = [row for row in lots if row.get("internal_lot")]
    # the receipt->lot link isn't projected on the list endpoint; fetch via quality-status by scanning
    # the most recently created lot for this material instead.
    return matches[-1]["id"]


async def _release(client, token, lot_id, expected_version, reason=None, container_ids=None):
    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(token),
        )
    ).json()
    body = {
        "idempotency_key": idem(),
        "lot_id": lot_id,
        "expected_version": expected_version,
        "reason": reason,
        "container_ids": container_ids,
        "challenge_id": challenge["challenge_id"],
        "reauth_password": "ChangeMe123!",
    }
    return await client.post(f"/materials/v1/lots/{lot_id}/release", json=body, headers=auth_headers(token))


async def _reject(client, token, lot_id, expected_version, reason="Failed inspection", container_ids=None):
    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges",
            json={"action": "reject"},
            headers=auth_headers(token),
        )
    ).json()
    body = {
        "idempotency_key": idem(),
        "lot_id": lot_id,
        "expected_version": expected_version,
        "reason": reason,
        "container_ids": container_ids,
        "challenge_id": challenge["challenge_id"],
        "reauth_password": "ChangeMe123!",
    }
    return await client.post(f"/materials/v1/lots/{lot_id}/reject", json=body, headers=auth_headers(token))


# --- RCV-FR-001/002/003/008/009/015 -----------------------------------------------------------------


async def test_receipt_examine_creates_lot_and_containers_in_quarantine(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id)
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-QTN")

    receipt = await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-QTN", container_count=3)
    assert receipt["resulting_version"] == 2

    receipt_detail = (await client.get(f"/materials/v1/receipts/{receipt_id}", headers=auth_headers(op_token))).json()
    assert receipt_detail["state"] == "examined"
    assert receipt_detail["discrepancy_type"] is None

    lots = (await client.get("/material-lots", params={"q": "LOT-QTN"}, headers=auth_headers(op_token))).json()["items"]
    assert len(lots) == 1
    assert lots[0]["status"] == "quarantine"
    assert lots[0]["available_quantity"] == "100.000000"


# --- RCV-FR-004: identity mismatch creates a hold, not a silent remapping -----------------------------


async def test_identity_mismatch_holds_receipt_no_lot_created(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-MISMATCH")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-MISMATCH")

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
            "identity_confirmed": False,
            "internal_lot": "LOT-MISMATCH",
            "discrepancy_reason": "Label does not match expected material code",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    receipt_detail = (await client.get(f"/materials/v1/receipts/{receipt_id}", headers=auth_headers(op_token))).json()
    assert receipt_detail["state"] == "discrepancy_hold"
    assert receipt_detail["discrepancy_type"] == "identity_mismatch"

    lots = (await client.get("/material-lots", params={"q": "LOT-MISMATCH"}, headers=auth_headers(op_token))).json()["items"]
    assert lots == []


async def test_identity_mismatch_without_reason_rejected(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-NOREASON")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-NOREASON")

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
            "identity_confirmed": False,
            "internal_lot": "LOT-NOREASON",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_damage_observed_holds_without_requiring_free_text_reason(client, seeded):
    """The visual-exam booleans are themselves the structured signal (RCV-FR-003) -- unlike an identity
    mismatch, damage/seal/contamination need no separate free-text reason to create the hold."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-DAMAGE")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-DAMAGE")

    resp = await client.post(
        f"/materials/v1/receipts/{receipt_id}/examine",
        json={
            "idempotency_key": idem(),
            "receipt_id": receipt_id,
            "expected_version": 1,
            "labeling_ok": True,
            "shipping_damage_observed": True,
            "container_damage_observed": False,
            "seal_broken": False,
            "identity_confirmed": True,
            "internal_lot": "LOT-DAMAGE",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    receipt_detail = (await client.get(f"/materials/v1/receipts/{receipt_id}", headers=auth_headers(op_token))).json()
    assert receipt_detail["state"] == "discrepancy_hold"
    assert receipt_detail["discrepancy_type"] == "damaged"
    assert receipt_detail["discrepancy_reason"]


async def test_container_damage_alone_also_holds_as_damaged(client, seeded):
    """Client gap-analysis Phase 6 (2026-10-05): "Damage observed" split into shipping/package damage vs.
    material container damage. Either one alone must still raise the same "damaged" discrepancy, and the
    legacy `damage_observed` column (kept for MIG-FR-004 compatibility) is the OR of the two."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-CONTAINER-DAMAGE")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-CONTAINER-DAMAGE")

    resp = await client.post(
        f"/materials/v1/receipts/{receipt_id}/examine",
        json={
            "idempotency_key": idem(),
            "receipt_id": receipt_id,
            "expected_version": 1,
            "labeling_ok": True,
            "shipping_damage_observed": False,
            "container_damage_observed": True,
            "seal_broken": False,
            "identity_confirmed": True,
            "internal_lot": "LOT-CONTAINER-DAMAGE",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    receipt_detail = (await client.get(f"/materials/v1/receipts/{receipt_id}", headers=auth_headers(op_token))).json()
    assert receipt_detail["state"] == "discrepancy_hold"
    assert receipt_detail["discrepancy_type"] == "damaged"
    assert receipt_detail["shipping_damage_observed"] is False
    assert receipt_detail["container_damage_observed"] is True
    assert receipt_detail["damage_observed"] is True


async def test_examine_rejects_removed_contamination_observed_field(client, seeded):
    """Client gap-analysis Phase 6: "Contamination observed" was dropped from the examination workflow
    entirely -- CommandEnvelope's extra="forbid" now rejects the old field outright rather than silently
    ignoring it."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-NO-CONTAMINATION")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-NO-CONTAMINATION")

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
            "contamination_observed": False,
            "identity_confirmed": True,
            "internal_lot": "LOT-NO-CONTAMINATION",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


# --- RCV-FR-005: coarse supplier-approval gate --------------------------------------------------------


async def test_unapproved_supplier_holds_receipt(client, seeded, db):
    from app.modules.supplier_quality.models import Supplier

    async with db.begin():
        supplier = Supplier(supplier_code="SUP-BAD", legal_name="Unapproved Supplier", role_type="supplier", status="draft")
        db.add(supplier)
        await db.flush()
        supplier_id = str(supplier.id)

    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-SUP")
    receipt_id = await _create_receipt(
        client, op_token, site_id, material_id, receipt_number="RCPT-SUP", supplier_id=supplier_id
    )
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-SUP")

    receipt_detail = (await client.get(f"/materials/v1/receipts/{receipt_id}", headers=auth_headers(op_token))).json()
    assert receipt_detail["state"] == "discrepancy_hold"
    assert receipt_detail["discrepancy_type"] == "source_not_approved"


# --- RCV-FR-018/019/020/022: sampling order + collect -> creates a qc_sample --------------------------


async def test_sampling_order_and_collect_creates_qc_sample(client, seeded, db):
    from sqlalchemy import select
    from app.modules.material.models import MaterialContainer, MaterialLot
    from app.modules.qc.models import QcSample

    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-SAMPLE")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-SAMPLE")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-SAMPLE", container_count=2)

    lot = (await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == "LOT-SAMPLE"))).scalar_one()
    containers = (
        (await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot.id)))
        .scalars()
        .all()
    )
    assert len(containers) == 2

    order_resp = await client.post(
        f"/materials/v1/lots/{lot.id}/sampling-orders",
        json={
            "idempotency_key": idem(),
            "lot_id": str(lot.id),
            "expected_version": 1,
            "selected_container_ids": [str(containers[0].id)],
            "assigned_sampler_user_id": str(seeded["users"]["qc.reviewer"].id),
        },
        headers=auth_headers(op_token),
    )
    assert order_resp.status_code == 200, order_resp.text
    order_id = order_resp.json()["aggregate_id"]

    lot_detail = (await client.get(f"/material-lots/{lot.id}", headers=auth_headers(qc_token))).json()
    assert lot_detail["status"] == "sampling"

    collect_resp = await client.post(
        f"/sampling-orders/{order_id}/collect",
        json={
            "idempotency_key": idem(),
            "sampling_order_id": order_id,
            "expected_version": 1,
            "sample_quantity": "1.000000",
            "sample_uom": "kg",
        },
        headers=auth_headers(qc_token),
    )
    assert collect_resp.status_code == 200, collect_resp.text

    lot_detail = (await client.get(f"/material-lots/{lot.id}", headers=auth_headers(qc_token))).json()
    assert lot_detail["status"] == "testing"

    samples = (await db.execute(select(QcSample).where(QcSample.source_type == "material_lot"))).scalars().all()
    assert len(samples) == 1
    assert str(samples[0].source_id) == str(lot.id)


async def test_sampling_order_container_not_in_lot_rejected(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-WRONGCTR")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-WRONGCTR")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-WRONGCTR", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await client.post(
        f"/materials/v1/lots/{lot_id}/sampling-orders",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "selected_container_ids": [str(uuid.uuid4())],
            "assigned_sampler_user_id": str(uuid.uuid4()),
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


# --- RCV-FR-026/027/029: release / reject / retest, Document 106 rows 44/45 ---------------------------


async def test_release_lot_signed_by_qa_releaser(client, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-REL")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-REL")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-REL", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await _release(client, qa_token, lot_id, expected_version=1)
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None

    lot_detail = (await client.get(f"/material-lots/{lot_id}", headers=auth_headers(qa_token))).json()
    assert lot_detail["status"] == "released"

    status = (await client.get(f"/materials/v1/lots/{lot_id}/quality-status", headers=auth_headers(qa_token))).json()
    assert status["eligible_for_use"] is True
    assert status["latest_disposition_decision"] == "released"


async def test_release_by_wrong_role_denied(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-RELWRONG")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-RELWRONG")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-RELWRONG", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await _release(client, op_token, lot_id, expected_version=1)
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_release_without_signature_challenge_rejected(client, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-NOSIG")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-NOSIG")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-NOSIG", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await client.post(
        f"/materials/v1/lots/{lot_id}/release",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "challenge_id": str(uuid.uuid4()),
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_CHALLENGE_INVALID"


async def test_reject_requires_reason(client, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-REJNOREASON")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-REJNOREASON")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-REJNOREASON", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await _reject(client, qa_token, lot_id, expected_version=1, reason="")
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_reject_lot_and_stale_version_retry_rejected(client, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-REJ")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-REJ")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-REJ", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await _reject(client, qa_token, lot_id, expected_version=1, reason="Failed visual inspection")
    assert resp.status_code == 200, resp.text

    lot_detail = (await client.get(f"/material-lots/{lot_id}", headers=auth_headers(qa_token))).json()
    assert lot_detail["status"] == "rejected"

    # Re-attempting reject at the now-stale version 1 must fail.
    stale_resp = await _reject(client, qa_token, lot_id, expected_version=1, reason="second try")
    assert stale_resp.status_code == 409
    assert stale_resp.json()["code"] == "STALE_VERSION"


async def test_release_of_already_disposed_lot_invalid_transition(client, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-DOUBLEREL")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-DOUBLEREL")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-DOUBLEREL", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await _release(client, qa_token, lot_id, expected_version=1)
    assert resp.status_code == 200, resp.text

    resp2 = await _release(client, qa_token, lot_id, expected_version=2)
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "INVALID_TRANSITION"


async def test_retest_material_lot(client, seeded):
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-RETEST")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-RETEST")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-RETEST", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await client.post(
        f"/materials/v1/lots/{lot_id}/retest",
        json={
            "idempotency_key": idem(),
            "lot_id": lot_id,
            "expected_version": 1,
            "reason": "Retest requested per stability schedule",
        },
        headers=auth_headers(qc_token),
    )
    assert resp.status_code == 200, resp.text

    lot_detail = (await client.get(f"/material-lots/{lot_id}", headers=auth_headers(qc_token))).json()
    assert lot_detail["status"] == "retest_due"


# --- RCV-FR-030: partial container disposition ---------------------------------------------------------


async def test_partial_container_release_does_not_change_lot_status(client, seeded, db):
    from sqlalchemy import select
    from app.modules.material.models import MaterialContainer, MaterialLot

    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-PARTIAL")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-PARTIAL")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-PARTIAL", container_count=2)

    lot = (await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == "LOT-PARTIAL"))).scalar_one()
    containers = (
        (await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot.id)))
        .scalars()
        .all()
    )
    assert len(containers) == 2

    resp = await _release(
        client, qa_token, str(lot.id), expected_version=1, container_ids=[str(containers[0].id)]
    )
    assert resp.status_code == 200, resp.text

    lot_detail = (await client.get(f"/material-lots/{lot.id}", headers=auth_headers(qa_token))).json()
    assert lot_detail["status"] == "quarantine"  # whole-lot status unaffected by a partial disposition

    await db.refresh(containers[0])
    assert containers[0].quality_status_override == "released"


# --- RCV-FR-023/025 partial gate: release-readiness surfaces QC evidence advisory, doesn't hard-block --


async def test_release_readiness_reports_qc_sample_evidence(client, seeded, db):
    from sqlalchemy import select
    from app.modules.material.models import MaterialLot

    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-READY")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-READY")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-READY", container_count=1)
    lot = (await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == "LOT-READY"))).scalar_one()

    readiness = (await client.get(f"/materials/v1/lots/{lot.id}/release-readiness", headers=auth_headers(op_token))).json()
    assert readiness["eligible_state"] is True
    assert readiness["receipt_discrepancy_clear"] is True
    assert readiness["sampling_complete"] is None
    assert readiness["qc_sample_ids"] == []


# --- RCV-FR-002: idempotent duplicate submission --------------------------------------------------------


async def test_duplicate_receipt_submission_idempotent(client, seeded):
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-DUP")

    key = idem()
    payload = {
        "idempotency_key": key,
        "site_id": str(site_id),
        "receipt_number": "RCPT-DUP",
        "material_id": material_id,
        "received_gross_quantity": "50.000000",
        "uom": "kg",
    }
    resp1 = await client.post("/materials/v1/receipts", json=payload, headers=auth_headers(op_token))
    resp2 = await client.post("/materials/v1/receipts", json=payload, headers=auth_headers(op_token))
    assert resp1.status_code == 200 and resp2.status_code == 200
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]


# --- RCV-FR-012: COA capture, hash, vault evidence linkage ---------------------------------------------


async def test_coa_document_hash_creates_vault_evidence(client, seeded, db):
    from sqlalchemy import select
    from app.modules.material.models import MaterialReceipt
    from app.modules.vault.models import VaultObject, VaultEvidence

    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-COA")

    resp = await client.post(
        "/materials/v1/receipts",
        json={
            "idempotency_key": idem(),
            "site_id": str(site_id),
            "receipt_number": "RCPT-COA",
            "material_id": material_id,
            "received_gross_quantity": "20.000000",
            "uom": "kg",
            "coa_document_hash": "a" * 64,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    receipt_id = resp.json()["aggregate_id"]

    receipt_row = await db.get(MaterialReceipt, uuid.UUID(receipt_id))
    assert receipt_row.coa_vault_object_id is not None
    assert receipt_row.coa_document_hash == "a" * 64

    vault_obj = await db.get(VaultObject, receipt_row.coa_vault_object_id)
    assert vault_obj is not None
    assert vault_obj.object_type == "material_coa"

    evidence_rows = (
        (await db.execute(select(VaultEvidence).where(VaultEvidence.vault_object_id == vault_obj.object_id)))
        .scalars()
        .all()
    )
    assert len(evidence_rows) == 1
    assert evidence_rows[0].evidence_sha256 == "a" * 64


# --- RCV-FR-026/027 independence: signer must differ from every production performer on the record -----


async def test_release_by_the_receiver_of_the_same_lot_denied(client, seeded, db):
    """Document 106 rows 44/45: signer MUST be independent of every production performer on the record.
    Grants the receiving operator the QA Releaser role too, so the only thing standing between them and a
    successful release is the independence check itself, not a missing permission."""
    from app.modules.iam.models import UserSiteRole

    async with db.begin():
        db.add(
            UserSiteRole(
                user_id=seeded["users"]["operator1"].id,
                site_id=seeded["site_id"],
                role_id=seeded["roles"]["QA Releaser"].id,
            )
        )

    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-SELFREL")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-SELFREL")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-SELFREL", container_count=1)
    lot_id = await _lot_id_for_receipt(client, receipt_id)

    resp = await _release(client, op_token, lot_id, expected_version=1)
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"
    assert "independent" in resp.json()["message"].lower()


# --- Client_Decisions_Neededanswers Topic 4: held-receipt disposition --------------------------------


async def _hold_receipt(client, op_token, site_id, code, receipt_number, internal_lot):
    """Creates a receipt and examines it into discrepancy_hold via an identity mismatch."""
    material_id = await _create_material(client, site_id, code=code)
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number=receipt_number)
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
            "identity_confirmed": False,
            "internal_lot": internal_lot,
            "discrepancy_reason": "Label does not match expected material code",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    return receipt_id


async def _disposition(client, token, receipt_id, expected_version, **body_overrides):
    challenge = (
        await client.post(
            f"/materials/v1/receipts/{receipt_id}/signature-challenges",
            json={"action": "disposition"},
            headers=auth_headers(token),
        )
    ).json()
    body = {
        "idempotency_key": idem(),
        "receipt_id": receipt_id,
        "expected_version": expected_version,
        "decision": "accepted",
        "severity": "minor",
        "reason": "Minor label discrepancy, supervisor-reviewed, safe to use",
        "challenge_id": challenge["challenge_id"],
        "reauth_password": "ChangeMe123!",
    }
    body.update(body_overrides)
    return await client.post(f"/materials/v1/receipts/{receipt_id}/disposition", json=body, headers=auth_headers(token))


async def test_disposition_minor_accept_creates_exception_flagged_lot(client, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    receipt_id = await _hold_receipt(client, op_token, site_id, "RM-DISP-MINOR", "RCPT-DISP-MINOR", "LOT-DISP-MINOR")

    resp = await _disposition(
        client, qa_token, receipt_id, expected_version=2,
        decision="accepted", severity="minor", internal_lot="LOT-DISP-MINOR",
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None

    receipt_detail = (await client.get(f"/materials/v1/receipts/{receipt_id}", headers=auth_headers(qa_token))).json()
    assert receipt_detail["state"] == "disposition_accepted"
    assert receipt_detail["disposition_decision"] == "accepted"
    assert receipt_detail["disposition_severity"] == "minor"
    assert receipt_detail["disposition_deviation_id"] is None

    lots = (await client.get("/material-lots", params={"q": "LOT-DISP-MINOR"}, headers=auth_headers(qa_token))).json()["items"]
    assert len(lots) == 1
    assert lots[0]["status"] == "quarantine"  # Q10: still enters normal quarantine, not released stock


async def test_disposition_significant_without_deviation_rejected(client, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    receipt_id = await _hold_receipt(client, op_token, site_id, "RM-DISP-SIG", "RCPT-DISP-SIG", "LOT-DISP-SIG")

    resp = await _disposition(client, qa_token, receipt_id, expected_version=2, severity="significant")
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"
    assert "deviation" in resp.json()["message"].lower()


async def test_disposition_significant_with_deviation_links_it(client, seeded, db):
    from app.modules.qms.models import DeviationRecord

    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    receipt_id = await _hold_receipt(client, op_token, site_id, "RM-DISP-SIG2", "RCPT-DISP-SIG2", "LOT-DISP-SIG2")

    async with db.begin():
        deviation = DeviationRecord(
            site_id=site_id, deviation_number="DEV-DISP-1", deviation_type="process",
            source_type="material_receipt", source_id=uuid.UUID(receipt_id), severity="major",
        )
        db.add(deviation)
        await db.flush()
        deviation_id = str(deviation.id)

    resp = await _disposition(
        client, qa_token, receipt_id, expected_version=2,
        decision="rejected", severity="significant", deviation_id=deviation_id,
        reason="Confirmed identity mismatch, deviation investigation closed, reject and return to supplier",
    )
    assert resp.status_code == 200, resp.text

    receipt_detail = (await client.get(f"/materials/v1/receipts/{receipt_id}", headers=auth_headers(qa_token))).json()
    assert receipt_detail["state"] == "disposition_rejected"
    assert receipt_detail["disposition_deviation_id"] == deviation_id

    lots = (await client.get("/material-lots", params={"q": "LOT-DISP-SIG2"}, headers=auth_headers(qa_token))).json()["items"]
    assert lots == []  # rejected -- no lot ever created


async def test_disposition_by_operator_role_denied(client, seeded):
    """Q8: the final decision must be made by an authorized QA/quality approver -- Operator lacks the
    material_receipt.disposition permission entirely."""
    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    receipt_id = await _hold_receipt(client, op_token, site_id, "RM-DISP-RBAC", "RCPT-DISP-RBAC", "LOT-DISP-RBAC")

    resp = await _disposition(client, op_token, receipt_id, expected_version=2, internal_lot="LOT-DISP-RBAC")
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_disposition_by_the_examiner_denied_as_not_independent(client, seeded, db):
    """Same independence precedent as material_lot.release/reject."""
    from app.modules.iam.models import UserSiteRole

    async with db.begin():
        db.add(
            UserSiteRole(
                user_id=seeded["users"]["operator1"].id,
                site_id=seeded["site_id"],
                role_id=seeded["roles"]["QA Releaser"].id,
            )
        )

    op_token = await login(client, "operator1")
    site_id = seeded["site_id"]
    receipt_id = await _hold_receipt(client, op_token, site_id, "RM-DISP-SELF", "RCPT-DISP-SELF", "LOT-DISP-SELF")

    resp = await _disposition(client, op_token, receipt_id, expected_version=2, internal_lot="LOT-DISP-SELF")
    assert resp.status_code == 422
    assert "independent" in resp.json()["message"].lower()


async def test_disposition_on_non_held_receipt_invalid_transition(client, seeded):
    op_token = await login(client, "operator1")
    qa_token = await login(client, "qa.releaser")
    site_id = seeded["site_id"]
    material_id = await _create_material(client, site_id, code="RM-DISP-CLEAN")
    receipt_id = await _create_receipt(client, op_token, site_id, material_id, receipt_number="RCPT-DISP-CLEAN")
    await _examine_clean(client, op_token, receipt_id, internal_lot="LOT-DISP-CLEAN")

    resp = await _disposition(client, qa_token, receipt_id, expected_version=2, internal_lot="LOT-DISP-CLEAN")
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"
