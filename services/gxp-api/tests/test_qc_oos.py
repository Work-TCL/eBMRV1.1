"""WP-04 / Document 25 (SPEC-QC-003) thin slice: OOS opened from a qc_result -> lab investigation ->
no-assignable-cause classification -> signed extended investigation -> retest/resample plan authorization
-> impact assessment -> signed disposition -> signed close (Document 106 rows 65-68), plus OOT evaluation
via the `rules` module and signed OOT close (row 69). CAPA/Change Control linkage, OOS `/reopen`, and
QA-review-package wiring remain out of scope (SG-074). SG-074 Task 3 (2026-09-23) added OOT-FR-006
release/QA-review blocking plus OOT reopen/dashboard/export and OOS dashboard/export."""

import uuid

from app.modules.qa_review import service as qa_review_service
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
from tests.test_release import _setup as _release_setup


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

    # classify-lab-cause before any investigation activity is rejected -- qa_reviewer_token, not
    # op_token, isolates this from the 2026-09-18 oos_record.classify_lab_cause RBAC gate (Operator no
    # longer holds it) so the assertion below exercises the business rule, not a permission denial.
    early = await client.post(
        f"/quality/oos/v1/{oos_id}/classify-lab-cause",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 1, "assignable": False},
        headers=auth_headers(qa_reviewer_token),
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
        headers=auth_headers(qa_reviewer_token),
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
        headers=auth_headers(qa_reviewer_token),
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

    record = (await client.get(f"/quality/oos/v1/{oos_id}", headers=auth_headers(qa_releaser_token))).json()
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
    # 2026-09-18: lab-investigation/classify-lab-cause/impact are now oos_record.* RBAC-gated to
    # QC Reviewer/QA Reviewer/Admin, not Operator -- qa_reviewer_token performs those steps so the OOS
    # record's version actually advances; op_token (Operator, who still lacks oos_record.close) remains
    # the actor asserted against at the end, exercising the real RBAC-driven 403 this test expects.
    qa_reviewer_token = await login(client, "qa.reviewer")

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
        headers=auth_headers(qa_reviewer_token),
    )
    await client.post(
        f"/quality/oos/v1/{oos_id}/classify-lab-cause",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 2, "assignable": True, "evidence_refs": ["evidence-1"]},
        headers=auth_headers(qa_reviewer_token),
    )
    await client.post(
        f"/quality/oos/v1/{oos_id}/impact",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 3, "impact_text": "No impact"},
        headers=auth_headers(qa_reviewer_token),
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


# ---------------------------------------------------------------------------
# SG-074 Task 3 (2026-09-23): OOT-FR-006 release/QA-review blocking, reopen, dashboard, export.
# ---------------------------------------------------------------------------


async def _open_oot_for_batch(client, db, seeded, tag, batch_id):
    """Trigger a real OOT via the rules module, attributed to `batch_id` (QcSample.source_type="batch"),
    the same attribution `_qc_signals()` in release/service.py and qa_review/service.py already use for
    OOS. Returns the oot_id of a freshly opened (state="open") OotRecord."""
    op_token = await login(client, "operator1")
    admin_token = await login(client, f"admin.oot.{tag}")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code=f"OOT-BLK-PROD-{tag}")
    await _author_and_release_rule(
        client, admin_token, db, rule_id=f"qc-trend:oot-blk-{tag}",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": f"OOT-BLK-SPEC-{tag}", "scope_type": "product",
            "scope_version_id": str(product_version.id),
            "test_definitions": [{
                "test_code": "ASSAY", "test_name": "Assay", "result_data_type": "numeric_single",
                "uom": "mg", "trend_rule_business_id": f"qc-trend:oot-blk-{tag}", "required": True, "release_blocking": True,
            }],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    spec_id = resp.json()["aggregate_id"]
    challenge = (
        await client.post(f"/qc/v1/specifications/{spec_id}/signature-challenges", json={"action": "release"}, headers=auth_headers(admin_token))
    ).json()
    resp = await client.post(
        f"/qc/v1/specifications/{spec_id}/release",
        json={
            "idempotency_key": idem(), "specification_id": spec_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={
                "idempotency_key": idem(), "sample_number": f"OOT-BLK-SAMPLE-{tag}", "sample_type": "in_process",
                "source_type": "batch", "source_id": batch_id,
            },
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
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_open_oot_blocks_release(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.oot.relblock")
    admin_token, batch_id = await _release_setup(db, client, seeded, "oot-relblock")
    oot_id = await _open_oot_for_batch(client, db, seeded, "relblock", batch_id)
    oot = await db.get(OotRecord, oot_id)
    assert oot.state == "open"

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["evaluation"]["eligible"] is False
    codes = {b["code"] for b in detail["evaluation"]["blockers"]}
    assert "OPEN_OOT" in codes


async def test_open_oot_blocks_qa_review_signal(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.oot.qablock")
    _admin_token, batch_id = await _release_setup(db, client, seeded, "oot-qablock", complete_review=False)
    oot_id = await _open_oot_for_batch(client, db, seeded, "qablock", batch_id)

    blockers, _warnings = await qa_review_service._qc_signals(db, uuid.UUID(batch_id))
    assert any(oot_id in b for b in blockers)


async def test_open_oos_from_batch_step_sourced_result_attributes_batch_id_and_blocks_release(client, seeded, db):
    """`open_oos_from_result` only stamped OosRecord.batch_id when the underlying QcSample was
    source_type="batch" -- a batch_step-sourced sample (the normal in-process-testing path) left it
    NULL, which would make the OOS invisible to release/service.py's open-OOS check (it reads
    OosRecord.batch_id directly, not through QcSample). Proves the fix end to end through the real
    API: create+start+complete a step-level sample/order/result, open an OOS from it, then confirm
    the OOS record is attributed to the batch and actually blocks release."""
    import uuid as uuid_mod

    from app.modules.qc.models import QcSample, QcTestOrder, QcTestRun, QcTestSpecification

    async with db.begin():
        await _make_admin(db, seeded, "admin.oos.batchstep")
    admin_token, batch_id = await _release_setup(db, client, seeded, "oos-batchstep")
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    step_id = view["steps"][0]["step_id"]

    async with db.begin():
        spec = QcTestSpecification(spec_code="SPEC-OOSBS", version_no=1, scope_type="in_process", scope_version_id=uuid_mod.uuid4(), status="released")
        db.add(spec)
        await db.flush()
        definition = QcTestDefinition(specification_id=spec.id, test_code="IPC-OOSBS", test_name="In-process check", result_data_type="numeric", required=True, release_blocking=True)
        db.add(definition)
        await db.flush()
        sample = QcSample(sample_number=f"SMP-OOSBS-{uuid_mod.uuid4().hex[:6]}", sample_type="in_process", source_type="batch_step", source_id=uuid_mod.UUID(step_id), state="testing_complete")
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
        result_id = str(qc_result.id)

    resp = await client.post(
        f"/quality/oos/v1/from-result/{result_id}",
        json={"idempotency_key": idem(), "source_result_id": result_id, "oos_number": "OOS-BATCHSTEP-1"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    oos_id = resp.json()["aggregate_id"]

    oos = await db.get(OosRecord, oos_id)
    assert oos.batch_id == uuid_mod.UUID(batch_id)

    resp = await client.post(
        f"/release/v1/scopes/batch/{batch_id}/evaluate",
        json={"idempotency_key": idem(), "scope_type": "batch", "scope_id": batch_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    scope_id = resp.json()["aggregate_id"]
    detail = (await client.get(f"/release/v1/scopes/{scope_id}/eligibility", headers=auth_headers(admin_token))).json()
    assert detail["evaluation"]["eligible"] is False
    codes = {b["code"] for b in detail["evaluation"]["blockers"]}
    assert "OPEN_OOS" in codes


async def test_reopen_closed_oot_record(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.oot.reopen")
    admin_token, batch_id = await _release_setup(db, client, seeded, "oot-reopen")
    oot_id = await _open_oot_for_batch(client, db, seeded, "reopen", batch_id)

    challenge = (
        await client.post(f"/quality/oot/v1/{oot_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(admin_token))
    ).json()
    resp = await client.post(
        f"/quality/oot/v1/{oot_id}/close",
        json={
            "idempotency_key": idem(), "oot_record_id": oot_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    # Not yet closed (stale version) -> INVALID_TRANSITION-class rejection, not a silent no-op.
    resp = await client.post(
        f"/quality/oot/v1/{oot_id}/reopen",
        json={
            "idempotency_key": idem(), "oot_record_id": oot_id, "expected_version": 1,
            "reason": "new information", "new_evidence": "supplier COA re-review",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"

    resp = await client.post(
        f"/quality/oot/v1/{oot_id}/reopen",
        json={
            "idempotency_key": idem(), "oot_record_id": oot_id, "expected_version": 2,
            "reason": "new information", "new_evidence": "supplier COA re-review",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    oot = await db.get(OotRecord, oot_id)
    assert oot.state == "open"
    assert oot.closed_at is None
    assert len(oot.reopen_history) == 1
    assert oot.reopen_history[0]["reason"] == "new information"


async def test_reopen_requires_permission(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.oot.reopenperm")
    admin_token, batch_id = await _release_setup(db, client, seeded, "oot-reopenperm")
    oot_id = await _open_oot_for_batch(client, db, seeded, "reopenperm", batch_id)
    challenge = (
        await client.post(f"/quality/oot/v1/{oot_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(admin_token))
    ).json()
    await client.post(
        f"/quality/oot/v1/{oot_id}/close",
        json={
            "idempotency_key": idem(), "oot_record_id": oot_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )

    op_token = await login(client, "operator1")
    resp = await client.post(
        f"/quality/oot/v1/{oot_id}/reopen",
        json={
            "idempotency_key": idem(), "oot_record_id": oot_id, "expected_version": 2,
            "reason": "new information", "new_evidence": "supplier COA re-review",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_oos_and_oot_dashboard_and_export(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.oot.dash")
    admin_token, batch_id = await _release_setup(db, client, seeded, "oot-dash")
    oot_id = await _open_oot_for_batch(client, db, seeded, "dash", batch_id)

    dashboard = (await client.get("/quality/oot/v1/dashboard", headers=auth_headers(admin_token))).json()
    assert dashboard["total"] >= 1
    assert dashboard["by_state"].get("open", 0) >= 1

    export = (await client.get("/quality/oot/v1/export", headers=auth_headers(admin_token))).json()
    assert any(row["id"] == oot_id for row in export)

    oos_dashboard = (await client.get("/quality/oos/v1/dashboard", headers=auth_headers(admin_token))).json()
    assert "by_state" in oos_dashboard and "by_severity" in oos_dashboard

    oos_export = (await client.get("/quality/oos/v1/export", headers=auth_headers(admin_token))).json()
    assert isinstance(oos_export, list)

    # New browsable list/detail reads backing the redesigned /quality/oos and /quality/oot list pages.
    oot_list = (await client.get("/quality/oot/v1", headers=auth_headers(admin_token))).json()
    assert "items" in oot_list and "total" in oot_list
    assert any(row["id"] == oot_id for row in oot_list["items"])

    oot_detail = (await client.get(f"/quality/oot/v1/{oot_id}", headers=auth_headers(admin_token))).json()
    assert oot_detail["id"] == oot_id
    assert oot_detail["state"] == "open"
    assert oot_detail["source_result_id"]

    oos_list = (await client.get("/quality/oos/v1", headers=auth_headers(admin_token))).json()
    assert "items" in oos_list and "total" in oos_list


# --- Client_Decisions_Neededanswers Topic 3: reopen, CAPA/Change-Control link, retest cap ------------


async def _oos_to_extended_investigation(client, db, seeded, tag, max_retests=None):
    """Mirrors test_full_oos_flow_no_assignable_cause's setup exactly, through the signed
    extended-investigation transition, parameterized so a retest-cap test can set max_retests on the
    governing QcTestDefinition. Returns (oos_id, definition_id, qa_reviewer_token, qa_releaser_token)."""
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")
    qa_reviewer_token = await login(client, "qa.reviewer")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code=f"OOS-PROD-{tag}")
        await _make_admin(db, seeded, f"admin.oos.{tag}")
        await _make_user(db, seeded, f"qa.reviewer.oos.{tag}", "QA Reviewer")
    admin_token = await login(client, f"admin.oos.{tag}")
    qa_reviewer2_token = await login(client, f"qa.reviewer.oos.{tag}")

    await _author_and_release_rule(
        client, admin_token, db, rule_id=f"qc-acceptance:oos-{tag}",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    spec_id = await _create_and_release_spec(
        client, qa_releaser_token, product_version.id, acceptance_rule_id=f"qc-acceptance:oos-{tag}",
        code=f"OOS-SPEC-{tag}", max_retests=max_retests,
    )
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": f"OOS-SAMPLE-{tag}", "sample_type": "finished_product", "source_type": "reserve"},
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

    oos_id = (
        await client.post(
            f"/quality/oos/v1/from-result/{result_id}",
            json={"idempotency_key": idem(), "source_result_id": result_id, "oos_number": f"OOS-{tag}"},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]

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
    return oos_id, definition_id, qa_reviewer_token, qa_releaser_token


async def _oos_to_closed(client, db, seeded, tag):
    """Extends _oos_to_extended_investigation through disposition + close -- returns oos_id."""
    oos_id, _definition_id, qa_reviewer_token, qa_releaser_token = await _oos_to_extended_investigation(client, db, seeded, tag)

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/impact",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 4,
            "impact_text": "No confirmed impact to other batches", "hold_status": "hold",
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text

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
    return oos_id, qa_releaser_token


async def test_reopen_closed_oos_record(client, seeded, db):
    oos_id, qa_releaser_token = await _oos_to_closed(client, db, seeded, "reopen1")

    oos = await db.get(OosRecord, oos_id)
    assert oos.state == "closed"
    assert oos.version == 7

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/reopen",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 7,
            "reason": "New stability data suggests the original root cause assessment was wrong",
            "new_evidence": "Stability report STB-2026-044 dated after closure",
            "target_state": "extended_investigation",
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 200, resp.text

    await db.refresh(oos)
    assert oos.state == "extended_investigation"
    assert oos.closed_at is None
    assert len(oos.reopen_history) == 1
    assert oos.reopen_history[0]["target_state"] == "extended_investigation"

    record = (await client.get(f"/quality/oos/v1/{oos_id}", headers=auth_headers(qa_releaser_token))).json()
    assert record["state"] == "extended_investigation"
    assert len(record["reopen_history"]) == 1


async def test_reopen_oos_invalid_target_state_rejected(client, seeded, db):
    oos_id, qa_releaser_token = await _oos_to_closed(client, db, seeded, "reopen2")

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/reopen",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 7,
            "reason": "x", "new_evidence": "y", "target_state": "closed",
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_reopen_oos_requires_permission(client, seeded, db):
    oos_id, _qa_releaser_token = await _oos_to_closed(client, db, seeded, "reopen3")
    op_token = await login(client, "operator1")

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/reopen",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 7,
            "reason": "x", "new_evidence": "y", "target_state": "extended_investigation",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_link_oos_to_change_control(client, seeded, db):
    from app.modules.qms.change_models import ChangeControl

    oos_id, _definition_id, qa_reviewer_token, _qa_releaser_token = await _oos_to_extended_investigation(client, db, seeded, "cc1")

    cc = ChangeControl(
        site_id=seeded["site_id"], change_number="CC-OOS-1", change_type="process", classification="minor",
        current_state={"note": "as-is"}, proposed_state={"note": "proposed"}, reason="Linked from OOS investigation",
        owner_subject_id=seeded["users"]["qa.reviewer"].id,
    )
    db.add(cc)
    await db.commit()

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/change-control",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 4, "change_control_id": str(cc.id)},
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text

    record = (await client.get(f"/quality/oos/v1/{oos_id}", headers=auth_headers(qa_reviewer_token))).json()
    assert record["change_control_id"] == str(cc.id)


async def test_link_oos_to_nonexistent_change_control_not_found(client, seeded, db):
    oos_id, _definition_id, qa_reviewer_token, _qa_releaser_token = await _oos_to_extended_investigation(client, db, seeded, "cc2")

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/change-control",
        json={"idempotency_key": idem(), "oos_record_id": oos_id, "expected_version": 4, "change_control_id": str(uuid.uuid4())},
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


async def test_retest_plan_within_cap_succeeds_then_exceeding_cap_rejected(client, seeded, db):
    oos_id, _definition_id, qa_reviewer_token, _qa_releaser_token = await _oos_to_extended_investigation(
        client, db, seeded, "cap1", max_retests=2
    )

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/retest-plans",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "justification": "Confirm assay via retest",
            "number_of_retests": 2, "method_ref": "HPLC-1",
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/quality/oos/v1/{oos_id}/retest-plans",
        json={
            "idempotency_key": idem(), "oos_record_id": oos_id, "justification": "One more retest needed",
            "number_of_retests": 1,
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "RETEST_NOT_AUTHORIZED"
    assert resp.json()["details"]["max_retests"] == 2
    assert resp.json()["details"]["already_authorized"] == 2
