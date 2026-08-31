"""WP-04 / Document 25 (SPEC-QC-003) thin slice: OOS opened from a qc_result -> lab investigation ->
no-assignable-cause classification -> signed extended investigation -> retest/resample plan authorization
-> impact assessment -> signed disposition -> signed close (Document 106 rows 65-68), plus OOT evaluation
via the `rules` module and signed OOT close (row 69). CAPA/Change Control linkage, `/reopen`, and
release-engine blocker wiring are out of scope this pass (SG-074)."""

from app.modules.qc.models import OosRecord, OosRetestPlan, OotRecord, QcResult, QcTestDefinition
from sqlalchemy import select
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_qc import (
    _author_and_release_rule,
    _create_and_release_spec,
    _make_admin,
    _make_user,
    _seed_product_version,
)


async def test_full_oos_flow_no_assignable_cause(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")
    qa_reviewer_token = await login(client, "qa.reviewer")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code="OOS-PROD-1")
        await _make_admin(db, seeded, "admin.oos1")
        await _make_user(db, seeded, "qa.reviewer.oos2", "QA Reviewer")
    admin_token = await login(client, "admin.oos1")
    qa_reviewer2_token = await login(client, "qa.reviewer.oos2")

    await _author_and_release_rule(
        client, admin_token, db, rule_id="qc-acceptance:oos-1",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    spec_id = await _create_and_release_spec(
        client, qa_releaser_token, product_version.id, acceptance_rule_id="qc-acceptance:oos-1", code="OOS-SPEC-1"
    )
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "OOS-SAMPLE-1", "sample_type": "finished_product", "source_type": "reserve"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    order_id = (
        await client.post(
            "/qc/v1/test-orders",
            json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    run_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/raw-data",
            json={"idempotency_key": idem(), "test_order_id": order_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    result_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/results",
            json={
                "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
                "result_type": "numeric_single", "value_decimal": "99.000000000000",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    result = await db.get(QcResult, result_id)
    assert result.outcome == "oos"

    # OpenOosFromResult -- unsigned (Doc 106 row 65).
    resp = await client.post(
        f"/quality/oos/v1/from-result/{result_id}",
        json={"idempotency_key": idem(), "source_result_id": result_id, "oos_number": "OOS-0001"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    oos_id = resp.json()["aggregate_id"]

    oos = await db.get(OosRecord, oos_id)
    assert oos.state == "open"
    assert oos.sample_id is not None
    assert oos.test_order_id is not None

    # Duplicate open is rejected.
    dup = await client.post(
        f"/quality/oos/v1/from-result/{result_id}",
        json={"idempotency_key": idem(), "source_result_id": result_id, "oos_number": "OOS-0002"},
        headers=auth_headers(op_token),
    )
    assert dup.status_code == 409
    assert dup.json()["code"] == "OOS_ALREADY_EXISTS"

    # classify-lab-cause before any investigation activity is rejected.
    early = await client.post(
        f"/quality/oos/v1/{oos_id}/classify-lab-cause",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 1, "assignable": False},
        headers=auth_headers(op_token),
    )
    assert early.status_code == 409
    assert early.json()["code"] == "INVESTIGATION_INCOMPLETE"

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/lab-investigation",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 1,
            "activity_type": "checklist_review", "response_text": "No obvious analyst/instrument error found",
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/classify-lab-cause",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 2, "assignable": False},
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    await db.refresh(oos)
    assert oos.state == "no_assignable_lab_cause"

    # Retest plan cannot be authorized before extended investigation starts.
    early_retest = await client.post(
        f"/quality/oos/v1/{oos_id}/retest-plans",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "justification": "too early", "number_of_retests": 1},
        headers=auth_headers(op_token),
    )
    assert early_retest.status_code == 409
    assert early_retest.json()["code"] == "RETEST_NOT_AUTHORIZED"

    # The investigator (qa.reviewer) holds the required role but is not independent of themselves --
    # SoD rejects a self-sign even though RBAC alone would allow it.
    same_actor_challenge = (
        await client.post(f"/quality/oos/v1/{oos_id}/signature-challenges", json={"action": "extended_investigation"}, headers=auth_headers(qa_reviewer_token))
    ).json()
    same_actor_resp = await client.post(
        f"/quality/oos/v1/{oos_id}/extended-investigation",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 3,
            "challenge_id": same_actor_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert same_actor_resp.status_code == 409
    assert same_actor_resp.json()["code"] == "INVALID_TRANSITION"

    challenge = (
        await client.post(f"/quality/oos/v1/{oos_id}/signature-challenges", json={"action": "extended_investigation"}, headers=auth_headers(qa_reviewer2_token))
    ).json()
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/extended-investigation",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 3,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_reviewer2_token),
    )
    assert resp.status_code == 200, resp.text
    await db.refresh(oos)
    assert oos.state == "extended_investigation"

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/retest-plans",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "justification": "Confirm assay via retest",
            "number_of_retests": 2, "method_ref": "HPLC-1",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    retest_plan = await db.get(OosRetestPlan, resp.json()["aggregate_id"])
    assert retest_plan.status == "authorized"

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/resample-plans",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "scientific_rationale": "Rule out sampling error"},
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/impact",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 4,
            "impact_text": "No confirmed impact to other batches; hold pending disposition", "hold_status": "hold",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    await db.refresh(oos)
    assert oos.state == "final_disposition"
    assert oos.hold_status == "hold"

    disp_challenge = (
        await client.post(f"/quality/oos/v1/{oos_id}/signature-challenges", json={"action": "disposition"}, headers=auth_headers(qa_releaser_token))
    ).json()
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/disposition",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 5,
            "final_classification": "laboratory_error", "challenge_id": disp_challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    await db.refresh(oos)
    assert oos.state == "qa_approval"
    assert oos.final_classification == "laboratory_error"

    close_challenge = (
        await client.post(f"/quality/oos/v1/{oos_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(qa_releaser_token))
    ).json()
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/close",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 6,
            "challenge_id": close_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    await db.refresh(oos)
    assert oos.state == "closed"
    assert oos.closed_at is not None

    record = (await client.get(f"/quality/oos/v1/{oos_id}")).json()
    assert record["state"] == "closed"
    assert len(record["activities"]) >= 3
    assert record["retest_plans"][0]["status"] == "authorized"

    # qc_result stays append-only (AG-08); the relationship is the reverse FK on oos_record.
    await db.refresh(oos)
    assert str(oos.source_result_id) == result_id


async def test_close_requires_independent_of_disposition_performer(client, seeded, db):
    """Closer independent of production performer/investigator (Doc 106 row 66) -- the operator who
    recorded the original result cannot also close the OOS they own."""
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code="OOS-PROD-2")

    spec_id = await _create_and_release_spec(client, qa_releaser_token, product_version.id, code="OOS-SPEC-2")
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )
    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "OOS-SAMPLE-2", "sample_type": "finished_product", "source_type": "reserve"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    order_id = (
        await client.post(
            "/qc/v1/test-orders",
            json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    run_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/raw-data",
            json={"idempotency_key": idem(), "test_order_id": order_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    result_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/results",
            json={
                "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
                "result_type": "numeric_single", "value_decimal": "5.000000000000",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    oos_id = (
        await client.post(
            f"/quality/oos/v1/from-result/{result_id}",
            json={"idempotency_key": idem(), "source_result_id": result_id, "oos_number": "OOS-SOD-1"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    # Fast-track straight through investigation/impact/disposition via the assignable-cause path.
    await client.post(
        f"/quality/oos/v1/{oos_id}/lab-investigation",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 1, "activity_type": "checklist_review"},
        headers=auth_headers(op_token),
    )
    await client.post(
        f"/quality/oos/v1/{oos_id}/classify-lab-cause",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 2, "assignable": True, "evidence_refs": ["evidence-1"]},
        headers=auth_headers(op_token),
    )
    await client.post(
        f"/quality/oos/v1/{oos_id}/impact",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 3, "impact_text": "No impact"},
        headers=auth_headers(op_token),
    )
    disp_challenge = (
        await client.post(f"/quality/oos/v1/{oos_id}/signature-challenges", json={"action": "disposition"}, headers=auth_headers(qa_releaser_token))
    ).json()
    await client.post(
        f"/quality/oos/v1/{oos_id}/disposition",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 4,
            "final_classification": "confirmed_oos", "challenge_id": disp_challenge["challenge_id"],
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )

    # Close before disposition would fail; verify the operator (production performer/investigator) is
    # rejected by SoD even though they never signed anything themselves.
    challenge = (
        await client.post(f"/quality/oos/v1/{oos_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(op_token))
    ).json()
    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/close",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 5,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_evaluate_oot_no_rule_configured(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code="OOT-PROD-1")

    spec_id = await _create_and_release_spec(client, qa_releaser_token, product_version.id, code="OOT-SPEC-1")
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )
    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "OOT-SAMPLE-1", "sample_type": "finished_product", "source_type": "reserve"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    order_id = (
        await client.post(
            "/qc/v1/test-orders",
            json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    run_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/raw-data",
            json={"idempotency_key": idem(), "test_order_id": order_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    result_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/results",
            json={
                "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
                "result_type": "numeric_single", "value_decimal": "5.000000000000",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    resp = await client.post(
        "/quality/oot/v1/evaluate",
        json={"idempotency_key": idem(), "source_result_id": result_id},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "OOT_RULE_NOT_RELEASED"


async def test_evaluate_oot_triggered_and_signed_close(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code="OOT-PROD-2")
        await _make_admin(db, seeded, "admin.oot1")
        await _make_user(db, seeded, "qa.releaser.oot2", "QA Releaser")
    admin_token = await login(client, "admin.oot1")
    qa_releaser2_token = await login(client, "qa.releaser.oot2")

    await _author_and_release_rule(
        client, admin_token, db, rule_id="qc-trend:oot-1",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )

    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "OOT-SPEC-2", "scope_type": "product",
            "scope_version_id": str(product_version.id),
            "test_definitions": [{
                "test_code": "ASSAY", "test_name": "Assay", "result_data_type": "numeric_single",
                "uom": "mg", "trend_rule_business_id": "qc-trend:oot-1", "required": True, "release_blocking": True,
            }],
        },
        headers=auth_headers(qa_releaser_token),
    )
    spec_id = resp.json()["aggregate_id"]
    challenge = (
        await client.post(f"/qc/v1/specifications/{spec_id}/signature-challenges", json={"action": "release"}, headers=auth_headers(qa_releaser_token))
    ).json()
    await client.post(
        f"/qc/v1/specifications/{spec_id}/release",
        json={
            "idempotency_key": idem(), "specification_id": spec_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "OOT-SAMPLE-2", "sample_type": "finished_product", "source_type": "reserve"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    order_id = (
        await client.post(
            "/qc/v1/test-orders",
            json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    run_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/raw-data",
            json={"idempotency_key": idem(), "test_order_id": order_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    # value=99 -> the trend rule (<=10.0) evaluates False -> triggered.
    result_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/results",
            json={
                "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
                "result_type": "numeric_single", "value_decimal": "99.000000000000",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

    resp = await client.post(
        "/quality/oot/v1/evaluate",
        json={"idempotency_key": idem(), "source_result_id": result_id},
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text
    oot_id = resp.json()["aggregate_id"]
    oot = await db.get(OotRecord, oot_id)
    assert oot.state == "open"
    assert oot.trigger_details["triggered"] is True

    # qc_result stays append-only (AG-08); the relationship is the reverse FK on oot_record.
    assert str(oot.source_result_id) == result_id

    # The investigation owner (qa.releaser) holds the required role but is not independent of themselves.
    same_actor_challenge = (
        await client.post(f"/quality/oot/v1/{oot_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(qa_releaser_token))
    ).json()
    same_actor_resp = await client.post(
        f"/quality/oot/v1/{oot_id}/close",
        json={
            "idempotency_key": idem(), "oot_record_id": oot_id, "expected_version": 1,
            "challenge_id": same_actor_challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert same_actor_resp.status_code == 409
    assert same_actor_resp.json()["code"] == "INVALID_TRANSITION"

    challenge = (
        await client.post(f"/quality/oot/v1/{oot_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(qa_releaser2_token))
    ).json()
    resp = await client.post(
        f"/quality/oot/v1/{oot_id}/close",
        json={
            "idempotency_key": idem(), "oot_record_id": oot_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser2_token),
    )
    assert resp.status_code == 200, resp.text
    await db.refresh(oot)
    assert oot.state == "closed"
    assert oot.closed_at is not None
