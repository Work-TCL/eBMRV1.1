"""Client requirement #11 -- the aggregated Batch Record view and its PDF export, stored as an
EvidenceObject owned by the batch through the existing stage->finalize evidence commands."""

import uuid

from sqlalchemy import select

from app.modules.equipment.commands import QUALIFIED_MARKER
from app.modules.equipment.models import EquipmentAsset, EquipmentUseLog
from app.modules.evidence.models import EvidenceObject
from app.modules.iam.models import User
from app.modules.material.models import Material, MaterialIssue, MaterialLot
from app.modules.qc.models import QcResult, QcSample, QcTestDefinition, QcTestOrder, QcTestRun, QcTestSpecification
from app.modules.qms.models import DeviationRecord
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_batch_execution import (
    _create_body,
    _issue_start_and_get_ready_step,
    _released_pair,
    _sign_step,
)


async def _complete_step(client, token, batch_id, step_id, expected_version):
    challenge_id = await _sign_step(client, token, batch_id, step_id, "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": expected_version, "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["resulting_version"]


async def test_batch_record_aggregates_execution_history_and_generates_pdf(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "rec1")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-REC-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    await _complete_step(client, admin_token, batch_id, step_id, ready_step["version"] + 1)

    async with db.begin():
        admin_user = (await db.execute(select(User).where(User.username == "admin.batchrec1"))).scalar_one()

        material = Material(site_id=seeded["site_id"], code="RM-REC1", name="Batch Record Material", uom="kg", status="active")
        db.add(material)
        await db.flush()
        lot = MaterialLot(
            material_id=material.id, site_id=seeded["site_id"], internal_lot=f"LOT-REC1-{uuid.uuid4().hex[:6]}",
            received_quantity="10", available_quantity="10", uom="kg", status="released",
            received_by_user_id=admin_user.id,
        )
        db.add(lot)
        await db.flush()
        db.add(MaterialIssue(material_lot_id=lot.id, batch_id=uuid.UUID(batch_id), quantity="1", uom="kg", issued_by_user_id=admin_user.id))

        asset = EquipmentAsset(site_id=seeded["site_id"], equipment_code=f"EQP-REC1-{uuid.uuid4().hex[:6]}", state=QUALIFIED_MARKER, version=1)
        db.add(asset)
        await db.flush()
        db.add(EquipmentUseLog(equipment_asset_id=asset.id, site_id=seeded["site_id"], log_type="use", batch_id=uuid.UUID(batch_id), operator_user_id=admin_user.id))

        db.add(
            DeviationRecord(
                site_id=seeded["site_id"], deviation_number=f"DEV-REC1-{uuid.uuid4().hex[:6]}", deviation_type="process",
                source_type="batch", source_id=uuid.UUID(batch_id), state="OPEN", severity="minor",
            )
        )

        spec = QcTestSpecification(spec_code="SPEC-REC1", version_no=1, scope_type="product", scope_version_id=uuid.uuid4(), status="released")
        db.add(spec)
        await db.flush()
        definition = QcTestDefinition(specification_id=spec.id, test_code="ASSAY", test_name="Assay", result_data_type="numeric", required=True, release_blocking=True)
        db.add(definition)
        await db.flush()
        sample = QcSample(sample_number=f"SMP-REC1-{uuid.uuid4().hex[:6]}", sample_type="finished_product", source_type="batch", source_id=uuid.UUID(batch_id), state="testing_complete")
        db.add(sample)
        await db.flush()
        order = QcTestOrder(sample_id=sample.id, test_definition_id=definition.id, state="reviewed", blocking=True)
        db.add(order)
        await db.flush()
        run = QcTestRun(test_order_id=order.id)
        db.add(run)
        await db.flush()
        db.add(QcResult(test_order_id=order.id, test_run_id=run.id, result_type="numeric", outcome="pass"))

    record = (await client.get(f"/batches/v1/{batch_id}/record", headers=auth_headers(admin_token))).json()
    assert record["batch"]["id"] == batch_id
    assert any(s["recipe_step_code"] == "STEP-A" and s["state"] == "complete" for s in record["steps"])
    assert len(record["materials_consumed"]) == 1
    assert record["materials_consumed"][0]["internal_lot"].startswith("LOT-REC1-")
    assert len(record["equipment_used"]) == 1
    assert len(record["deviations"]) == 1
    assert record["deviations"][0]["deviation_number"].startswith("DEV-REC1-")
    assert len(record["qc_results"]) == 1
    assert record["qc_results"][0]["outcome"] == "pass"
    assert len(record["status_history"]) > 0

    resp = await client.post(
        f"/batches/v1/{batch_id}/record:generate-pdf",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    evidence_id = resp.json()["aggregate_id"]

    evidence = await db.get(EvidenceObject, uuid.UUID(evidence_id))
    assert evidence is not None
    assert evidence.owner_type == "batch"
    assert str(evidence.owner_id) == batch_id
    assert evidence.state == "FINALIZED"
    assert evidence.mime_type == "application/pdf"
    assert evidence.size_bytes and evidence.size_bytes > 0


async def test_batch_record_rejects_unknown_batch(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.get(f"/batches/v1/{uuid.uuid4()}/record", headers=auth_headers(op_token))
    assert resp.status_code == 404, resp.text
