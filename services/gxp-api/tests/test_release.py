"""Document 15 (SPEC-EBMR-006) -- the buildable slice: evaluate a release scope (get-or-create +
eligibility from real signals: QA review currency/completeness, batch hold state, Vault integrity),
release (signature-gated, re-evaluates immediately before commit, creates a Vault release package
snapshot), hold, and reject. New module. Rework/reprocess/destroy and non-batch scope types are out of
scope this pass -- SG-056.
"""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.rel"):
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


async def _released_product_and_recipe(client, admin_token, site_id, tag):
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": f"RELPRD-{tag}", "product_code": f"RELPRD-{tag}",
            "name": "Release Test Product", "version_no": 1, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
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

    resp = await client.post(
        "/recipes/v2/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": f"RELPRD-{tag}", "recipe_code": f"RELRCP-{tag}", "version_no": 1,
            "product_version_id": product_version_id, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
            "sections": [{"stable_section_code": "SEC-1", "name": "Dispensing", "sequence": 1}],
            "steps": [{"stable_step_code": "STEP-A", "section_code": "SEC-1", "step_type": "weigh", "sequence_hint": 1}],
            "dependencies": [],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    recipe_version_id = resp.json()["aggregate_id"]
    await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/release",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return product_version_id, recipe_version_id


async def _sign_step(client, token, batch_id, step_id, action):
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/signature-challenges",
        json={"action": action},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def _sign_batch(client, token, batch_id, action):
    resp = await client.post(
        f"/batches/v1/{batch_id}/signature-challenges",
        json={"action": action},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def _setup(db, client, seeded, tag, *, complete_review=True):
    async with db.begin():
        await _make_admin(db, seeded, f"admin.rel{tag}")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="qa_review_package", action="complete", meaning="Reviewed", signature_required=False))
        db.add(SignaturePolicy(record_type="release_scope", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="release_scope", action="hold", meaning="Approved", signature_required=False))
        db.add(SignaturePolicy(record_type="release_scope", action="reject", meaning="Rejected", signature_required=False))
    admin_token = await login(client, f"admin.rel{tag}")
    product_version_id, recipe_version_id = await _released_product_and_recipe(client, admin_token, seeded["site_id"], tag)

    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": f"BAT-REL-{tag}",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    # SG-180 (2026-09-17, project-owner-directed): release eligibility now also requires
    # `batch.state == "production_complete"` (REL-FR-003's "manufacturing completeness"). Drive the
    # single-step recipe (STEP-A, no parameters/evidence) all the way through so every test in this file
    # still represents a batch that is actually eligible to be evaluated/released, unless a test
    # deliberately wants to hit that specific blocker.
    resp = await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    step = next(s for s in view["steps"] if s["state"] == "ready")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step["step_id"], "expected_version": step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    challenge_id = await _sign_step(client, admin_token, batch_id, step["step_id"], "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step['step_id']}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step["step_id"],
            "expected_version": step["version"] + 1,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    challenge_id = await _sign_batch(client, admin_token, batch_id, "production_complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/production-complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "expected_version": view["batch"]["version"],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    if complete_review:
        resp = await client.post(
            f"/qa-review/v1/batches/{batch_id}/packages",
            json={"idempotency_key": idem(), "batch_id": batch_id},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200, resp.text
        package_id = resp.json()["aggregate_id"]
        resp = await client.post(
            f"/qa-review/v1/packages/{package_id}/complete",
            json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 1},
            headers=auth_headers(admin_token),
        )
        assert resp.status_code == 200, resp.text

    return admin_token, batch_id


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post(
        "/release/v1/scopes/batch/00000000-0000-0000-0000-000000000000/evaluate", json={"idempotency_key": idem()}, headers={}
    )
    assert resp.status_code == 401


async def test_evaluate_requires_permission(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "1")
    op_token = await login(client, "operator1")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_evaluate_blocked_without_qa_review(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "2", complete_review=False)
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "blocked"
    assert detail["evaluation"]["eligible"] is False
    codes = {b["code"] for b in detail["evaluation"]["blockers"]}
    assert "QA_REVIEW_MISSING" in codes


async def test_evaluate_eligible_and_release(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "3")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "eligible"
    assert detail["evaluation"]["eligible"] is True
    assert detail["evaluation"]["blockers"] == []

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    package = (await client.get(f"/release/v1/scopes/{scope_id}/package", headers=auth_headers(admin_token))).json()
    assert package["scope"]["state"] == "released"
    assert package["scope"]["released_vault_object_id"] is not None
    assert package["decisions"][-1]["decision_code"] == "RELEASED"
    assert package["decisions"][-1]["release_package_hash"] is not None


async def test_evaluate_blocked_by_open_deviation(client, seeded, db):
    """SG-059 RESOLVED 2026-09-18, project-owner-directed (asked directly: any open deviation vs.
    critical/major-only vs. don't block -- chose 'any open deviation attributed to the batch')."""
    admin_token, batch_id = await _setup(db, client, seeded, "7")
    import uuid as uuid_mod

    from sqlalchemy import select

    from app.modules.qms.models import DeviationRecord

    async with db.begin():
        admin_user = (await db.execute(select(User).where(User.username == "admin.rel7"))).scalar_one()
        deviation = DeviationRecord(
            site_id=seeded["site_id"], deviation_number=f"DEV-REL-TEST-7-{uuid_mod.uuid4().hex[:6]}",
            deviation_type="process", source_type="batch", source_id=uuid_mod.UUID(batch_id),
            severity="major", owner_subject_id=admin_user.id, state="OPEN",
        )
        db.add(deviation)
        await db.flush()
        deviation_id = deviation.id

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "blocked"
    blockers = [b for b in detail["evaluation"]["blockers"] if b["code"] == "OPEN_DEVIATION"]
    assert len(blockers) == 1
    assert blockers[0]["source_id"] == str(deviation_id)

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"

    # Close the deviation -- the blocker clears on re-evaluation.
    async with db.begin():
        dev = await db.get(DeviationRecord, deviation_id)
        dev.state = "CLOSED"

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["evaluation"]["eligible"] is True
    assert not any(b["code"] == "OPEN_DEVIATION" for b in detail["evaluation"]["blockers"])


async def test_evaluate_blocked_by_qc_material_em_signals(client, seeded, db):
    """2026-09-19, project-owner-directed: release eligibility now also checks QC (failing result on a
    release-blocking test order), materials (a consumed lot never cleared for use) and environmental
    monitoring (an action-excursion reading) attributed to the batch. One row of each, inserted directly
    the same way the OPEN_DEVIATION test above inserts a DeviationRecord -- these three modules' own
    create-command ceremonies are exercised by their own test suites (test_qc.py/test_material_flow.py/
    test_em_flow.py); this test only proves release/service.py reads what they'd produce."""
    import uuid as uuid_mod
    from decimal import Decimal

    from sqlalchemy import select

    from app.modules.equipment.em_models import EmSampleOrReading
    from app.modules.material.models import Material, MaterialIssue, MaterialLot
    from app.modules.qc.models import QcResult, QcSample, QcTestDefinition, QcTestOrder, QcTestRun, QcTestSpecification

    admin_token, batch_id = await _setup(db, client, seeded, "8")

    async with db.begin():
        admin_user = (await db.execute(select(User).where(User.username == "admin.rel8"))).scalar_one()

        spec = QcTestSpecification(spec_code="SPEC-REL8", version_no=1, scope_type="product", scope_version_id=uuid_mod.uuid4(), status="released")
        db.add(spec)
        await db.flush()
        definition = QcTestDefinition(specification_id=spec.id, test_code="ASSAY", test_name="Assay", result_data_type="numeric", required=True, release_blocking=True)
        db.add(definition)
        await db.flush()
        sample = QcSample(sample_number=f"SMP-REL8-{uuid_mod.uuid4().hex[:6]}", sample_type="in_process", source_type="batch", source_id=uuid_mod.UUID(batch_id), state="testing_complete")
        db.add(sample)
        await db.flush()
        order = QcTestOrder(sample_id=sample.id, test_definition_id=definition.id, state="reviewed", blocking=True)
        db.add(order)
        await db.flush()
        run = QcTestRun(test_order_id=order.id)
        db.add(run)
        await db.flush()
        qc_result = QcResult(test_order_id=order.id, test_run_id=run.id, result_type="numeric", outcome="oos")
        db.add(qc_result)
        await db.flush()
        qc_result_id = qc_result.id

        material = Material(site_id=seeded["site_id"], code="RM-REL8", name="Release Test Material", uom="kg", status="active")
        db.add(material)
        await db.flush()
        lot = MaterialLot(
            material_id=material.id, site_id=seeded["site_id"], internal_lot=f"LOT-REL8-{uuid_mod.uuid4().hex[:6]}",
            received_quantity=Decimal("10"), available_quantity=Decimal("10"), uom="kg", status="quarantine",
            received_by_user_id=admin_user.id,
        )
        db.add(lot)
        await db.flush()
        db.add(MaterialIssue(material_lot_id=lot.id, batch_id=uuid_mod.UUID(batch_id), quantity=Decimal("1"), uom="kg", issued_by_user_id=admin_user.id))
        lot_id = lot.id

        em_location_id = next(iter(seeded["em_locations"].values())).id
        reading = EmSampleOrReading(
            site_id=seeded["site_id"], program_version_id=seeded["em_program"].id, location_id=em_location_id,
            monitoring_type="viable_air", batch_id=uuid_mod.UUID(batch_id), alert_action_status="action_excursion", state="REVIEWED",
        )
        db.add(reading)
        await db.flush()
        em_reading_id = reading.id

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "blocked"
    assert detail["evaluation"]["eligible"] is False
    blockers_by_code = {b["code"]: b for b in detail["evaluation"]["blockers"]}
    assert blockers_by_code["QC_RESULT_FAILED"]["source_id"] == str(qc_result_id)
    assert blockers_by_code["MATERIAL_LOT_NOT_RELEASED"]["source_id"] == str(lot_id)
    assert blockers_by_code["EM_ACTION_EXCURSION"]["source_id"] == str(em_reading_id)

    # Releasing the lot clears exactly its own blocker, not the others.
    async with db.begin():
        released_lot = await db.get(MaterialLot, lot_id)
        released_lot.status = "released"

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    codes = {b["code"] for b in detail["evaluation"]["blockers"]}
    assert "MATERIAL_LOT_NOT_RELEASED" not in codes
    assert "QC_RESULT_FAILED" in codes
    assert "EM_ACTION_EXCURSION" in codes


async def test_evaluate_blocked_by_incomplete_qc_testing(client, seeded, db):
    """Client requirement #10: a release-blocking test order that has never even reached a terminal/
    reviewed state (no result recorded at all here) blocks release with QC_TESTING_INCOMPLETE -- distinct
    from QC_RESULT_FAILED, which only fires for a *recorded* failing outcome."""
    import uuid as uuid_mod

    from app.modules.qc.models import QcSample, QcTestDefinition, QcTestOrder, QcTestSpecification

    admin_token, batch_id = await _setup(db, client, seeded, "10")

    async with db.begin():
        spec = QcTestSpecification(spec_code="SPEC-REL10", version_no=1, scope_type="product", scope_version_id=uuid_mod.uuid4(), status="released")
        db.add(spec)
        await db.flush()
        definition = QcTestDefinition(specification_id=spec.id, test_code="ASSAY", test_name="Assay", result_data_type="numeric", required=True, release_blocking=True)
        db.add(definition)
        await db.flush()
        sample = QcSample(sample_number=f"SMP-REL10-{uuid_mod.uuid4().hex[:6]}", sample_type="in_process", source_type="batch", source_id=uuid_mod.UUID(batch_id), state="testing_complete")
        db.add(sample)
        await db.flush()
        order = QcTestOrder(sample_id=sample.id, test_definition_id=definition.id, state="analyst_complete", blocking=True)
        db.add(order)
        await db.flush()
        order_id = order.id

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["evaluation"]["eligible"] is False
    blockers_by_code = {b["code"]: b for b in detail["evaluation"]["blockers"]}
    assert blockers_by_code["QC_TESTING_INCOMPLETE"]["source_id"] == str(order_id)
    assert "QC_RESULT_FAILED" not in blockers_by_code

    # Once the order reaches a terminal state, the blocker clears.
    async with db.begin():
        reviewed = await db.get(QcTestOrder, order_id)
        reviewed.state = "reviewed"

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    codes = {b["code"] for b in detail["evaluation"]["blockers"]}
    assert "QC_TESTING_INCOMPLETE" not in codes


async def test_evaluate_warnings_are_non_blocking(client, seeded, db):
    """QC 'oot', EM 'alert' and an incomplete packaging run are all real signals (2026-09-19) but
    deliberately warning-only -- project-owner-directed: OOT/alert are watch-level, not confirmed
    failures, and packaging is not a release gate at all. None of them may appear in `blockers` or flip
    `eligible` to false."""
    import uuid as uuid_mod

    from app.modules.batch_execution.models import Batch
    from app.modules.equipment.em_models import EmSampleOrReading
    from app.modules.packaging.models import PackagingRun
    from app.modules.qc.models import QcResult, QcSample, QcTestDefinition, QcTestOrder, QcTestRun, QcTestSpecification

    admin_token, batch_id = await _setup(db, client, seeded, "9")

    async with db.begin():
        batch = await db.get(Batch, uuid_mod.UUID(batch_id))
        spec = QcTestSpecification(spec_code="SPEC-REL9", version_no=1, scope_type="product", scope_version_id=uuid_mod.uuid4(), status="released")
        db.add(spec)
        await db.flush()
        definition = QcTestDefinition(specification_id=spec.id, test_code="ASSAY", test_name="Assay", result_data_type="numeric", required=True, release_blocking=True)
        db.add(definition)
        await db.flush()
        sample = QcSample(sample_number=f"SMP-REL9-{uuid_mod.uuid4().hex[:6]}", sample_type="in_process", source_type="batch", source_id=uuid_mod.UUID(batch_id), state="testing_complete")
        db.add(sample)
        await db.flush()
        order = QcTestOrder(sample_id=sample.id, test_definition_id=definition.id, state="reviewed", blocking=True)
        db.add(order)
        await db.flush()
        run = QcTestRun(test_order_id=order.id)
        db.add(run)
        await db.flush()
        db.add(QcResult(test_order_id=order.id, test_run_id=run.id, result_type="numeric", outcome="oot"))

        em_location_id = next(iter(seeded["em_locations"].values())).id
        db.add(
            EmSampleOrReading(
                site_id=seeded["site_id"], program_version_id=seeded["em_program"].id, location_id=em_location_id,
                monitoring_type="viable_air", batch_id=uuid_mod.UUID(batch_id), alert_action_status="alert", state="REVIEWED",
            )
        )

        db.add(
            PackagingRun(
                site_id=seeded["site_id"], batch_id=uuid_mod.UUID(batch_id),
                product_version_id=batch.product_version_id, state="in_progress", reconciliation_state="not_started",
            )
        )

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "eligible"
    assert detail["evaluation"]["eligible"] is True
    assert detail["evaluation"]["blockers"] == []
    warning_codes = {w["code"] for w in detail["evaluation"]["warnings"]}
    assert warning_codes == {"QC_RESULT_OOT", "EM_ALERT", "PACKAGING_INCOMPLETE"}

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_evaluate_blocked_by_equipment_and_capa_signals(client, seeded, db):
    """2026-09-19, project-owner-directed follow-up (equipment + CAPA):

    Equipment: `EquipmentUseLog` now records which asset satisfied a step's requirement
    (batch_execution/commands.py::start_step); release re-checks that asset's *current* eligibility
    (equipment_commands.get_eligibility) so a batch is caught if its equipment went on hold afterward.

    CAPA: `CAPA_SOURCE_TYPES` deliberately does NOT gain "batch" (Document 27 names exactly 11 source
    types and "batch" isn't one -- see release/service.py::_capa_signals docstring). Instead this checks
    the real 2-hop path: a CAPA whose source is a deviation/OOS that IS attributed to this batch."""
    import uuid as uuid_mod
    from datetime import datetime, timezone

    from sqlalchemy import select

    from app.modules.equipment.models import EquipmentAsset, EquipmentUseLog
    from app.modules.qms.capa_models import CapaRecord
    from app.modules.qms.models import DeviationRecord

    admin_token, batch_id = await _setup(db, client, seeded, "10")

    async with db.begin():
        admin_user = (await db.execute(select(User).where(User.username == "admin.rel10"))).scalar_one()

        asset = EquipmentAsset(
            site_id=seeded["site_id"], equipment_code=f"EQ-REL10-{uuid_mod.uuid4().hex[:6]}",
            state="QUALIFIED_AVAILABLE", qualification_status="QUALIFIED",
            hold_flag=True, hold_source="manual", hold_reason="Found leaking post-use",
        )
        db.add(asset)
        await db.flush()
        db.add(
            EquipmentUseLog(
                equipment_asset_id=asset.id, site_id=seeded["site_id"], log_type="production",
                batch_id=uuid_mod.UUID(batch_id), operator_user_id=admin_user.id, source="system",
            )
        )
        asset_id = asset.id

        deviation = DeviationRecord(
            site_id=seeded["site_id"], deviation_number=f"DEV-REL10-{uuid_mod.uuid4().hex[:6]}",
            deviation_type="process", source_type="batch", source_id=uuid_mod.UUID(batch_id),
            severity="major", owner_subject_id=admin_user.id, state="CLOSED",
        )
        db.add(deviation)
        await db.flush()
        capa = CapaRecord(
            site_id=seeded["site_id"], capa_number=f"CAPA-REL10-{uuid_mod.uuid4().hex[:6]}",
            source_type="deviation", source_id=deviation.id, problem_statement="Recurring leak",
            risk_class="medium", root_cause_ref={"note": "test"}, state="OPEN",
            owner_subject_id=admin_user.id, target_date=datetime.now(timezone.utc),
        )
        db.add(capa)
        await db.flush()
        capa_id = capa.id

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "blocked"
    blockers_by_code = {b["code"]: b for b in detail["evaluation"]["blockers"]}
    assert blockers_by_code["EQUIPMENT_OUT_OF_SERVICE"]["source_id"] == str(asset_id)
    assert blockers_by_code["OPEN_CAPA"]["source_id"] == str(capa_id)

    # Closing the CAPA and releasing the equipment from hold clears both blockers.
    async with db.begin():
        released_asset = await db.get(EquipmentAsset, asset_id)
        released_asset.hold_flag = False
        closed_capa = await db.get(CapaRecord, capa_id)
        closed_capa.state = "CLOSED"

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["evaluation"]["eligible"] is True, detail["evaluation"]["blockers"]


async def test_evaluate_blocked_by_yield_reconciliation_signals(client, seeded, db):
    """2026-09-19, project-owner-directed follow-up, correcting a stale claim: Document 17 (yield/
    reconciliation) was NOT "never built" -- `yield_reconciliation/commands.py::get_batch_summary`
    already computed a `release_blocked` flag from `_UNRESOLVED_STATES = (FAILED, OUT_OF_LIMIT,
    OUT_OF_TOLERANCE)` (YLD-FR-028/029's own "release-blocker flag"), it was just never consulted from
    release/service.py. A calculated-but-not-yet-verified row is a non-blocking warning; a SUPERSEDED row
    (the module's own append-only correction marker) counts as neither."""
    import uuid as uuid_mod

    from app.modules.yield_reconciliation.models import ManufacturingCalculation, ReconciliationRecord

    admin_token, batch_id = await _setup(db, client, seeded, "11")

    async with db.begin():
        calc = ManufacturingCalculation(
            site_id=seeded["site_id"], batch_id=uuid_mod.UUID(batch_id), calculation_type="YIELD",
            input_refs={"note": "test"}, input_hash="deadbeef", state="OUT_OF_LIMIT",
        )
        db.add(calc)
        rec = ReconciliationRecord(
            site_id=seeded["site_id"], batch_id=uuid_mod.UUID(batch_id), reconciliation_type="MATERIAL",
            item_ref={"note": "test"}, quantities={"consumed": "10"}, state="CALCULATED",
        )
        db.add(rec)
        # A superseded row (e.g. a prior failed run someone already corrected) must NOT still block.
        superseded = ManufacturingCalculation(
            site_id=seeded["site_id"], batch_id=uuid_mod.UUID(batch_id), calculation_type="POTENCY",
            input_refs={"note": "test"}, input_hash="deadbeef2", state="SUPERSEDED",
        )
        db.add(superseded)
        await db.flush()
        calc_id, rec_id = calc.id, rec.id

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "blocked"
    blockers_by_code = {b["code"]: b for b in detail["evaluation"]["blockers"]}
    assert blockers_by_code["YIELD_CALCULATION_UNRESOLVED"]["source_id"] == str(calc_id)
    warning_codes = {w["code"]: w for w in detail["evaluation"]["warnings"]}
    assert warning_codes["RECONCILIATION_NOT_VERIFIED"]["source_id"] == str(rec_id)

    async with db.begin():
        fixed_calc = await db.get(ManufacturingCalculation, calc_id)
        fixed_calc.state = "VERIFIED"

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert not any(b["code"] == "YIELD_CALCULATION_UNRESOLVED" for b in detail["evaluation"]["blockers"])


async def test_release_rejected_when_blocked(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "4", complete_review=False)
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_hold_keeps_eligibility_updating_but_blocks_release(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "5")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/hold",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2, "reason": "quality investigation"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "hold"

    # Re-evaluate: eligibility recomputes (still eligible), but state stays "hold" -- REL-FR-011.
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "hold"
    assert detail["evaluation"]["eligible"] is True

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 4},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_reject(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "6")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/reject",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2, "reason": "customer complaint pattern"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["scope"]["state"] == "rejected"


async def test_post_release_hold_preserves_release_decision_history(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "10")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/hold",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 3, "reason": "field complaint under investigation"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    package = (await client.get(f"/release/v1/scopes/{scope_id}/package", headers=auth_headers(admin_token))).json()
    assert package["scope"]["state"] == "hold"
    codes = [d["decision_code"] for d in package["decisions"]]
    assert codes == ["RELEASED", "HOLD"]  # original RELEASED decision retained, never edited/removed


async def test_stale_version_rejected(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "7")
    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 99},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "8")
    key = idem()
    body = {"idempotency_key": key, "scope_type": "batch", "scope_id": batch_id}
    resp1 = await client.post(f"/release/v1/scopes/batch/{batch_id}/evaluate", json=body, headers=auth_headers(admin_token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post(f"/release/v1/scopes/batch/{batch_id}/evaluate", json=body, headers=auth_headers(admin_token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_release_fails_closed_pending_signature_policy(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.rel9")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="qa_review_package", action="complete", meaning="Reviewed", signature_required=False))
        # Deliberately no SignaturePolicy(record_type="release_scope", action="release", ...) row.
    admin_token = await login(client, "admin.rel9")
    product_version_id, recipe_version_id = await _released_product_and_recipe(client, admin_token, seeded["site_id"], "9")
    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": "BAT-REL-9",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    # SG-180: drive the single step to completion + Production Complete so this test still reaches the
    # signature-policy check it's actually testing, instead of tripping the new PRODUCTION_NOT_COMPLETE
    # blocker first.
    await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    step = next(s for s in view["steps"] if s["state"] == "ready")
    await client.post(
        f"/batches/v1/{batch_id}/steps/{step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step["step_id"], "expected_version": step["version"]},
        headers=auth_headers(admin_token),
    )
    challenge_id = await _sign_step(client, admin_token, batch_id, step["step_id"], "complete")
    await client.post(
        f"/batches/v1/{batch_id}/steps/{step['step_id']}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step["step_id"],
            "expected_version": step["version"] + 1,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    challenge_id = await _sign_batch(client, admin_token, batch_id, "production_complete")
    await client.post(
        f"/batches/v1/{batch_id}/production-complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "expected_version": view["batch"]["version"],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )

    resp = await client.post(
        f"/qa-review/v1/batches/{batch_id}/packages",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(admin_token),
    )
    package_id = resp.json()["aggregate_id"]
    await client.post(
        f"/qa-review/v1/packages/{package_id}/complete",
        json={"idempotency_key": idem(), "package_id": package_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    scope_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/release/v1/scopes/{scope_id}/release",
        json={"idempotency_key": idem(), "scope_id": scope_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"
