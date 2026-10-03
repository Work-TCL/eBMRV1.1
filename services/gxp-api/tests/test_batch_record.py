"""Client requirement #11 -- the aggregated Batch Record view and its PDF export, stored as an
EvidenceObject owned by the batch through the existing stage->finalize evidence commands."""

import uuid
from datetime import datetime

from sqlalchemy import select

from app.modules.equipment.aseptic_models import AsepticOperation
from app.modules.equipment.commands import QUALIFIED_MARKER
from app.modules.equipment.models import EquipmentAsset, EquipmentUseLog
from app.modules.equipment.sterilization_models import ProcessCycle
from app.modules.evidence.models import EvidenceObject
from app.modules.iam.models import User
from app.modules.qc.models import QcResult, QcSample, QcTestDefinition, QcTestOrder, QcTestRun, QcTestSpecification
from app.modules.qms.capa_models import CapaRecord
from app.modules.qms.models import DeviationRecord
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_batch_execution import (
    _create_body,
    _issue_start_and_get_ready_step,
    _make_user_with_role,
    _released_pair,
    _sign_step,
)
from tests.test_material_consumption_flow import consume_material_into_existing_batch


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
    completed_version = await _complete_step(client, admin_token, batch_id, step_id, ready_step["version"] + 1)

    # 2026-09-22: a real MaterialConsumption row (Dispense -> Record consumption), not a hand-inserted
    # `MaterialIssue` row -- that table is retired and `record_service.py` no longer reads it. Uses the
    # standard seeded operator/QC/QA-releaser trio (same as test_material_flow.py) rather than
    # `admin_token`, which this fixture's own per-test admin doesn't hold every dispensing permission for.
    op_token = await login(client, "operator1")
    qc_token = await login(client, "qc.reviewer")
    qa_releaser_token = await login(client, "qa.releaser")
    lot_id, _dc_id = await consume_material_into_existing_batch(
        client, db, seeded, op_token, qc_token, qa_releaser_token, batch_id, step_id, "RM-REC1", f"LOT-REC1-{uuid.uuid4().hex[:6]}"
    )
    # The helper above ran plain reads through the shared `db` fixture session (e.g. looking up the
    # DispensingSource row), which autobegins a transaction that stays open until closed explicitly --
    # close it before the next `async with db.begin()` block, which requires none open. `commit`, not
    # `rollback` -- SessionLocal has expire_on_commit=False, but rollback always expires every object
    # regardless, which would break the later `seeded["roles"][...]` attribute access below.
    await db.commit()

    async with db.begin():
        admin_user = (await db.execute(select(User).where(User.username == "admin.batchrec1"))).scalar_one()

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
    # Read-path completeness fix: source_id was queried but dropped from the response, so a "batch_step"
    # deviation couldn't be attributed to its step client-side even though the backend already knows it.
    assert record["deviations"][0]["source_id"] == batch_id
    assert len(record["qc_results"]) == 1
    assert record["qc_results"][0]["outcome"] == "pass"
    assert len(record["status_history"]) > 0

    # build_full_batch_record()'s new sections (step instructions/evidence/comments/handovers/holds/
    # corrections) need at least one populated row each to prove the PDF path handles them without
    # erroring -- a step comment is the simplest to add post-completion.
    comment_resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/comments",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": completed_version, "comment_text": "Balance checked before weighing.",
        },
        headers=auth_headers(admin_token),
    )
    assert comment_resp.status_code == 200, comment_resp.text

    # SG-137 (2026-09-22): the batch-record PDF export is now signed by a QA Releaser.
    async with db.begin():
        await _make_user_with_role(db, seeded, "qa.batchrec1", "QA Releaser")
    qa_token = await login(client, "qa.batchrec1")
    challenge_resp = await client.post(
        f"/batches/v1/{batch_id}/signature-challenges", json={"action": "record_export"}, headers=auth_headers(qa_token),
    )
    assert challenge_resp.status_code == 200, challenge_resp.text
    challenge = challenge_resp.json()
    resp = await client.post(
        f"/batches/v1/{batch_id}/record:generate-pdf",
        json={
            "idempotency_key": idem(), "batch_id": batch_id,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
    evidence_id = resp.json()["aggregate_id"]

    evidence = await db.get(EvidenceObject, uuid.UUID(evidence_id))
    assert evidence is not None
    assert evidence.owner_type == "batch"
    assert str(evidence.owner_id) == batch_id
    assert evidence.state == "FINALIZED"
    assert evidence.mime_type == "application/pdf"
    assert evidence.size_bytes and evidence.size_bytes > 0

    # Bug fix (2026-09-29): QA Releaser is the sole signer of record_export but held no evidence.*
    # permission at all, so the actor who generates the PDF could never retrieve it through the real
    # HTTP download endpoint -- only caught by a live user, since the assertions above go straight to
    # the DB and bypass the permission layer entirely. Exercise the actual download path this time.
    download_resp = await client.get(
        f"/evidence/v1/{evidence_id}/download?purpose=inspection", headers=auth_headers(qa_token)
    )
    assert download_resp.status_code == 200, download_resp.text
    assert download_resp.headers["content-type"] == "application/pdf"
    assert download_resp.content.startswith(b"%PDF")


async def test_batch_record_rejects_unknown_batch(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.get(f"/batches/v1/{uuid.uuid4()}/record", headers=auth_headers(op_token))
    assert resp.status_code == 404, resp.text


async def test_workspace_returns_null_release_and_qa_review_when_none_exist_yet(client, seeded, db):
    # Batch Workspace: a freshly issued batch has no release scope and no QA review package yet -- the
    # endpoint must return null (matching release/router.py's own get_scope_by_target convention), not
    # 404 or an empty-shaped object, and empty lists (not an error) for CAPA/aseptic/sterilization
    # activity it genuinely has none of.
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ws1")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-WS-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]

    resp = await client.get(f"/batches/v1/{batch_id}/workspace", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["batch"]["id"] == batch_id
    # Real labels, not bare UUIDs -- the Workspace batch dict resolves site/product/recipe codes so the
    # page never has to show a raw product_version_id/recipe_version_id/site_id to the user.
    assert body["batch"]["site_code"] is not None
    assert body["batch"]["product_code"] is not None
    assert body["batch"]["recipe_code"] is not None
    assert body["batch"]["recipe_version_no"] == 1
    assert body["release"]["scope_id"] is None
    assert body["release"]["eligible"] is None
    assert body["release"]["blockers"] == []
    assert body["qa_review_package"] is None
    assert body["capas"] == []
    assert body["aseptic_operations"] == []
    assert body["sterilization_cycles"] == []


async def test_workspace_steps_are_ordered_by_dependency(client, seeded, db):
    # Batch Workspace step wizard: _released_pair's own recipe is two steps, STEP-A -> STEP-B (a real
    # dependency, not just insertion order) -- proves get_batch_workspace()'s topological sort actually
    # orders by the dependency graph, not raw DB/insertion order, and that predecessor/successor codes
    # round-trip correctly.
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ws3")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-WS-3"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]

    # Step instances don't exist until the batch is issued (they're created from the frozen recipe
    # snapshot at issue time) -- issue only, not start, so states stay at their just-issued ready/pending.
    resp = await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/batches/v1/{batch_id}/workspace", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    steps = resp.json()["steps"]
    assert [s["recipe_step_code"] for s in steps] == ["STEP-A", "STEP-B"]
    assert steps[0]["predecessor_codes"] == []
    assert steps[0]["successor_codes"] == ["STEP-B"]
    assert steps[1]["predecessor_codes"] == ["STEP-A"]
    assert steps[1]["successor_codes"] == []
    # STEP-A has no predecessor so it's immediately ready; STEP-B is blocked on it.
    assert steps[0]["state"] == "ready"
    assert steps[1]["state"] == "pending"


async def test_workspace_aggregates_capa_aseptic_and_sterilization_activity(client, seeded, db):
    # Bug fix / feature: CAPA has no direct batch_id, so this proves the source_type="deviation" ->
    # source_id join actually resolves; aseptic/sterilization previously had a batch_id column with no
    # batch-scoped read at all.
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ws2")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-WS-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]

    async with db.begin():
        admin_user = (await db.execute(select(User).where(User.username == "admin.batchws2"))).scalar_one()

        deviation = DeviationRecord(
            site_id=seeded["site_id"], deviation_number=f"DEV-WS2-{uuid.uuid4().hex[:6]}", deviation_type="process",
            source_type="batch", source_id=uuid.UUID(batch_id), state="OPEN", severity="minor",
        )
        db.add(deviation)
        await db.flush()

        db.add(
            CapaRecord(
                site_id=seeded["site_id"], capa_number=f"CAPA-WS2-{uuid.uuid4().hex[:6]}",
                source_type="deviation", source_id=deviation.id, problem_statement="Test problem",
                risk_class="medium", root_cause_ref={"proactive_rationale": "test"}, state="OPEN",
                owner_subject_id=admin_user.id, target_date=datetime(2027, 1, 1),
            )
        )

        asset = EquipmentAsset(site_id=seeded["site_id"], equipment_code=f"EQP-WS2-{uuid.uuid4().hex[:6]}", state=QUALIFIED_MARKER, version=1)
        db.add(asset)
        await db.flush()

        db.add(EquipmentUseLog(equipment_asset_id=asset.id, site_id=seeded["site_id"], log_type="use", batch_id=uuid.UUID(batch_id), operator_user_id=admin_user.id))

        db.add(
            AsepticOperation(
                site_id=seeded["site_id"], batch_id=uuid.UUID(batch_id), area_id=seeded["areas"]["AREA-GRADE-C"].id,
                profile_version_id=seeded["aseptic_profile"].id, state="PREPARATION",
            )
        )
        db.add(
            ProcessCycle(
                site_id=seeded["site_id"], batch_id=uuid.UUID(batch_id), process_type="steam_autoclave",
                equipment_id=asset.id, profile_version_id=seeded["sterilization_profile"].id, state="DRAFT",
            )
        )

    resp = await client.get(f"/batches/v1/{batch_id}/workspace", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["deviations"]) == 1
    assert len(body["capas"]) == 1
    assert body["capas"][0]["capa_number"].startswith("CAPA-WS2-")
    assert body["capas"][0]["source_id"] == str(deviation.id)
    assert len(body["equipment_used"]) == 1
    assert body["equipment_used"][0]["equipment_code"] == asset.equipment_code
    assert len(body["aseptic_operations"]) == 1
    assert body["aseptic_operations"][0]["state"] == "PREPARATION"
    assert body["aseptic_operations"][0]["area_code"] == seeded["areas"]["AREA-GRADE-C"].area_code
    assert len(body["sterilization_cycles"]) == 1
    assert body["sterilization_cycles"][0]["process_type"] == "steam_autoclave"
    assert body["sterilization_cycles"][0]["equipment_code"] == asset.equipment_code


async def test_generate_pdf_rejects_actor_without_qa_releaser_role(client, seeded, db):
    """SG-137: Admin alone does not hold QA Releaser, so the role check rejects before signature is even
    considered."""
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "rec2")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-REC-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/batches/v1/{batch_id}/record:generate-pdf",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_generate_pdf_requires_a_signature_from_the_qa_releaser(client, seeded, db):
    """SG-137: correct role, but no challenge -> MISSING_SIGNATURE."""
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "rec3")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-REC-3"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    async with db.begin():
        await _make_user_with_role(db, seeded, "qa.batchrec3", "QA Releaser")
    qa_token = await login(client, "qa.batchrec3")

    resp = await client.post(
        f"/batches/v1/{batch_id}/record:generate-pdf",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"
