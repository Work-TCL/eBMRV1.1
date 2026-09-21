"""WP-04 / Document 23 (SPEC-QC-001) thin slice: test specification draft/release (scope_type=product,
SUP...QC-FR-001/002) -> sample create/receive (QC-FR-005..009) -> test order create/start (QC-FR-010/011)
-> raw data + result recording with acceptance-rule-driven PASS/OOS/pending classification (QC-FR-018/019/
025/026, reusing the existing `rules` module) -> analyst completion + signed second-person review
(QC-FR-022/023) -> the 2-signature result correction ceremony (QC-FR-024, Document 106 row 57).
scope_type="material", instrument eligibility, and actual OOS/OOT record creation are out of scope this
pass (SG-057/SG-063)."""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.product_master.models import ProductVersion
from app.modules.qc.models import QcResult, QcResultCorrection, QcSample, QcTestOrder, QcTestSpecification
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_user(db, seeded, username, role_name):
    user = User(
        username=username, email=f"{username}@example.com", full_name=username,
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


async def _make_admin(db, seeded, username="admin.qc"):
    return await _make_user(db, seeded, username, "Admin")


async def _seed_product_version(db, seeded, code="QC-PROD-1"):
    pv = ProductVersion(
        product_business_id=code, version_no=1, product_code=code, name="QC Test Product",
        manufacturing_profile_code="oral_solid", lifecycle_state="released", site_id=seeded["site_id"],
    )
    db.add(pv)
    await db.flush()
    return pv


async def _author_and_release_rule(client, admin_token, db, *, rule_id, expression_ast):
    async with db.begin():
        db.add(SignaturePolicy(record_type="rule", action="release", meaning="Released", signature_required=False))

    resp = await client.post(
        "/rules/v1/drafts",
        json={
            "idempotency_key": idem(), "rule_id": rule_id, "rule_type": "qc_acceptance", "semantic_version": "1.0.0",
            "expression_ast": expression_ast,
            "input_contract": {"value": {"type": "decimal"}},
            "output_contract": {"pass": {"type": "boolean"}},
            "unit_policy": {}, "precision_policy": {"calculation_class": "CC-3"},
            "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    rule_object_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/validate",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/release",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return rule_object_id


async def _create_and_release_spec(client, admin_token, product_version_id, acceptance_rule_id=None, code="SPEC-1"):
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": code, "scope_type": "product",
            "scope_version_id": str(product_version_id),
            "test_definitions": [{
                "test_code": "ASSAY", "test_name": "Assay", "result_data_type": "numeric_single",
                "uom": "mg", "acceptance_rule_business_id": acceptance_rule_id, "required": True,
                "release_blocking": True,
            }],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    spec_id = resp.json()["aggregate_id"]

    challenge = (
        await client.post(
            f"/qc/v1/specifications/{spec_id}/signature-challenges", json={"action": "release"},
            headers=auth_headers(admin_token),
        )
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
    return spec_id


async def test_material_scope_rejected(client, seeded, db):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "SPEC-MAT", "scope_type": "material",
            "scope_version_id": idem(),
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_full_qc_flow_pass_result(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")
    qa_reviewer_token = await login(client, "qa.reviewer")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded)
        await _make_admin(db, seeded, "admin.qc1")
    admin_token = await login(client, "admin.qc1")

    rule_id = await _author_and_release_rule(
        client, admin_token, db, rule_id="qc-acceptance:assay",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    spec_id = await _create_and_release_spec(
        client, qa_releaser_token, product_version.id, acceptance_rule_id="qc-acceptance:assay"
    )

    spec = await db.get(QcTestSpecification, spec_id)
    definitions_resp = spec  # sanity: released
    assert definitions_resp.status == "released"

    from sqlalchemy import select
    from app.modules.qc.models import QcTestDefinition

    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_resp = await client.post(
        "/qc/v1/samples",
        json={
            "idempotency_key": idem(), "sample_number": "SAMPLE-1", "sample_type": "finished_product",
            "source_type": "reserve",
        },
        headers=auth_headers(op_token),
    )
    assert sample_resp.status_code == 200, sample_resp.text
    sample_id = sample_resp.json()["aggregate_id"]

    resp = await client.post(
        "/qc/v1/samples/" + sample_id + "/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    order_resp = await client.post(
        "/qc/v1/test-orders",
        json={
            "idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id,
        },
        headers=auth_headers(op_token),
    )
    assert order_resp.status_code == 200, order_resp.text
    order_id = order_resp.json()["aggregate_id"]

    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1, "analyst_id": None},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    raw_data_resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/raw-data",
        json={"idempotency_key": idem(), "test_order_id": order_id, "method_version": "HPLC-1"},
        headers=auth_headers(op_token),
    )
    assert raw_data_resp.status_code == 200, raw_data_resp.text
    run_id = raw_data_resp.json()["aggregate_id"]

    result_resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/results",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
            "result_type": "numeric_single", "value_decimal": "5.000000000000", "uom": "mg",
        },
        headers=auth_headers(op_token),
    )
    assert result_resp.status_code == 200, result_resp.text
    result_id = result_resp.json()["aggregate_id"]

    result = await db.get(QcResult, result_id)
    assert result.outcome == "pass"
    # Client requirements #2/#3 (2026-09-21): "mg" is now a baseline released rules.gxp_uom row (see
    # conftest.py's `seeded` fixture) and record_result hardens uom resolution via
    # `_resolve_uom_id_strict` -- the dual-write resolves.
    assert result.uom == "mg"
    assert result.uom_id is not None

    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/complete",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 2},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    challenge = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/signature-challenges", json={"action": "review"},
            headers=auth_headers(qa_reviewer_token),
        )
    ).json()
    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/review",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "expected_version": 3,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 200, resp.text

    order = await db.get(QcTestOrder, order_id)
    assert order.state == "reviewed"

    readiness = await client.get(f"/qc/v1/release-readiness?sample_id={sample_id}")
    assert readiness.json()["ready"] is True

    record = await client.get(f"/qc/v1/samples/{sample_id}/record")
    assert record.json()["test_orders"][0]["results"][0]["outcome"] == "pass"


async def test_result_out_of_spec_and_correction_flow(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")
    qc_reviewer_token = await login(client, "qc.reviewer")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded)
        second_qc = await _make_user(db, seeded, "qc.reviewer2", "QC Reviewer")
        await _make_admin(db, seeded, "admin.qc2")
    second_qc_token = await login(client, "qc.reviewer2")
    admin_token = await login(client, "admin.qc2")

    await _author_and_release_rule(
        client, admin_token, db, rule_id="qc-acceptance:assay-2",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    spec_id = await _create_and_release_spec(
        client, qa_releaser_token, product_version.id, acceptance_rule_id="qc-acceptance:assay-2", code="SPEC-2"
    )

    from sqlalchemy import select
    from app.modules.qc.models import QcTestDefinition

    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "SAMPLE-OOS", "sample_type": "finished_product", "source_type": "reserve"},
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

    result_resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/results",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
            "result_type": "numeric_single", "value_decimal": "99.000000000000",
        },
        headers=auth_headers(op_token),
    )
    result_id = result_resp.json()["aggregate_id"]
    result = await db.get(QcResult, result_id)
    assert result.outcome == "oos"

    order = await db.get(QcTestOrder, order_id)
    assert order.state == "oos_pending"

    # QC-FR-024: correction requires 2 signatures from 2 different people.
    challenge = (
        await client.post(
            f"/qc/v1/results/{result_id}/signature-challenges", json={"action": "correct_request"},
            headers=auth_headers(qc_reviewer_token),
        )
    ).json()
    resp = await client.post(
        f"/qc/v1/results/{result_id}/correct",
        json={
            "idempotency_key": idem(), "result_id": result_id, "reason_text": "Transcription error in raw value",
            "corrected_value_decimal": "5.000000000000",
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qc_reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    correction_id = resp.json()["aggregate_id"]

    # Same corrector cannot also approve (SoD).
    challenge2 = (
        await client.post(
            f"/qc/v1/results/{result_id}/signature-challenges", json={"action": "correct_approve"},
            headers=auth_headers(qc_reviewer_token),
        )
    ).json()
    resp = await client.post(
        f"/qc/v1/corrections/{correction_id}/approve",
        json={
            "idempotency_key": idem(), "correction_id": correction_id,
            "challenge_id": challenge2["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qc_reviewer_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"

    challenge3 = (
        await client.post(
            f"/qc/v1/results/{result_id}/signature-challenges", json={"action": "correct_approve"},
            headers=auth_headers(second_qc_token),
        )
    ).json()
    resp = await client.post(
        f"/qc/v1/corrections/{correction_id}/approve",
        json={
            "idempotency_key": idem(), "correction_id": correction_id,
            "challenge_id": challenge3["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(second_qc_token),
    )
    assert resp.status_code == 200, resp.text
    new_result_id = resp.json()["aggregate_id"]

    new_result = await db.get(QcResult, new_result_id)
    assert new_result.outcome == "oos"  # original outcome carried forward; only the value/audit trail change
    assert str(new_result.supersedes_result_id) == result_id
    assert new_result.value_decimal is not None

    correction = await db.get(QcResultCorrection, correction_id)
    assert correction.status == "completed"

    original = await db.get(QcResult, result_id)
    assert original.value_decimal == 99  # original row never edited


async def test_result_pending_without_released_rule(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded)

    spec_id = await _create_and_release_spec(client, qa_releaser_token, product_version.id, acceptance_rule_id=None, code="SPEC-3")

    from sqlalchemy import select
    from app.modules.qc.models import QcTestDefinition

    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "SAMPLE-PEND", "sample_type": "finished_product", "source_type": "reserve"},
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

    result_resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/results",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
            "result_type": "numeric_single", "value_decimal": "5.000000000000",
        },
        headers=auth_headers(op_token),
    )
    result = await db.get(QcResult, result_resp.json()["aggregate_id"])
    assert result.outcome == "pending"


async def test_complete_blocked_without_required_result(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded)

    spec_id = await _create_and_release_spec(client, qa_releaser_token, product_version.id, code="SPEC-4")

    from sqlalchemy import select
    from app.modules.qc.models import QcTestDefinition

    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )
    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "SAMPLE-INC", "sample_type": "finished_product", "source_type": "reserve"},
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

    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/complete",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 2},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "RAW_DATA_REQUIRED"


async def test_review_requires_independent_reviewer(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded)

    spec_id = await _create_and_release_spec(client, qa_releaser_token, product_version.id, code="SPEC-5")

    from sqlalchemy import select
    from app.modules.qc.models import QcTestDefinition

    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )
    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "SAMPLE-SOD", "sample_type": "finished_product", "source_type": "reserve"},
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
            json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id, "assigned_analyst_id": None},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1, "analyst_id": None},
        headers=auth_headers(op_token),
    )
    run_id = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/raw-data",
            json={"idempotency_key": idem(), "test_order_id": order_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/test-orders/{order_id}/results",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
            "result_type": "numeric_single", "value_decimal": "5.000000000000",
        },
        headers=auth_headers(op_token),
    )
    await client.post(
        f"/qc/v1/test-orders/{order_id}/complete",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 2},
        headers=auth_headers(op_token),
    )

    challenge = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/signature-challenges", json={"action": "review"},
            headers=auth_headers(op_token),
        )
    ).json()
    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/review",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "expected_version": 3,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_review_stale_version_rejected(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")
    qa_reviewer_token = await login(client, "qa.reviewer")

    async with db.begin():
        product_version = await _seed_product_version(db, seeded)

    spec_id = await _create_and_release_spec(client, qa_releaser_token, product_version.id, code="SPEC-6")

    from sqlalchemy import select
    from app.modules.qc.models import QcTestDefinition

    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )
    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={"idempotency_key": idem(), "sample_number": "SAMPLE-STALE", "sample_type": "finished_product", "source_type": "reserve"},
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
    await client.post(
        f"/qc/v1/test-orders/{order_id}/results",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
            "result_type": "numeric_single", "value_decimal": "5.000000000000",
        },
        headers=auth_headers(op_token),
    )
    await client.post(
        f"/qc/v1/test-orders/{order_id}/complete",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 2},
        headers=auth_headers(op_token),
    )

    challenge = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/signature-challenges", json={"action": "review"},
            headers=auth_headers(qa_reviewer_token),
        )
    ).json()
    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/review",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "expected_version": 99,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_reviewer_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"
