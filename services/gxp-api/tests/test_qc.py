"""WP-04 / Document 23 (SPEC-QC-001) thin slice: test specification draft/release (scope_type=product,
SUP...QC-FR-001/002) -> sample create/receive (QC-FR-005..009) -> test order create/start (QC-FR-010/011)
-> raw data + result recording with acceptance-rule-driven PASS/OOS/pending classification (QC-FR-018/019/
025/026, reusing the existing `rules` module) -> analyst completion + signed second-person review
(QC-FR-022/023) -> the 2-signature result correction ceremony (QC-FR-024, Document 106 row 57).
scope_type="material", instrument eligibility, and actual OOS/OOT record creation are out of scope this
pass (SG-057/SG-063)."""

from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.modules.iam.models import Qualification, User, UserSiteRole
from sqlalchemy import select
from app.modules.material.models import Material, MaterialContainer, MaterialLot, MaterialReceipt
from app.modules.material_specification.models import MaterialSpecificationVersion
from app.modules.product_master.models import ProductVersion
from app.modules.qc.models import (
    QcResult,
    QcResultCorrection,
    QcSample,
    QcTestDefinition,
    QcTestOrder,
    QcTestSpecification,
)
from app.modules.signature.models import SignaturePolicy
from app.modules.supplier_quality.models import Supplier
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


async def _create_and_release_spec(client, admin_token, product_version_id, acceptance_rule_id=None, code="SPEC-1", max_retests=None):
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": code, "scope_type": "product",
            "scope_version_id": str(product_version_id),
            "test_definitions": [{
                "test_code": "ASSAY", "test_name": "Assay", "result_data_type": "numeric_single",
                "uom": "mg", "acceptance_rule_business_id": acceptance_rule_id, "required": True,
                "release_blocking": True, "max_retests": max_retests,
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


async def test_unknown_scope_type_rejected(client, seeded, db):
    """SG-076: scope_type="material" is now buildable (MaterialSpecificationVersion exists); the generic
    BUILDABLE_SCOPE_TYPES check still rejects a genuinely unknown scope_type."""
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "SPEC-WIDGET", "scope_type": "widget",
            "scope_version_id": idem(),
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_material_scope_unknown_scope_version_id_not_found(client, seeded, db):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "SPEC-MAT-404", "scope_type": "material",
            "scope_version_id": idem(),
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


async def test_material_scope_accepted_and_round_trips(client, seeded, db):
    """SG-076: scope_type="material" referencing a real MaterialSpecificationVersion is now buildable."""
    async with db.begin():
        material = Material(site_id=seeded["site_id"], code="MAT-QC-SCOPE-001", name="QC Scope Material", uom="kg")
        db.add(material)
        await db.flush()
        matspec = MaterialSpecificationVersion(
            material_spec_business_id="MATSPEC-QC-1", version_no=1, material_id=material.id,
            name="QC Scope Material Spec", lifecycle_state="released", site_id=seeded["site_id"],
        )
        db.add(matspec)
        await db.flush()
        matspec_id = matspec.id

    op_token = await login(client, "operator1")
    resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "SPEC-MAT-OK", "scope_type": "material",
            "scope_version_id": str(matspec_id),
            "test_definitions": [{
                "test_code": "IDENTITY", "test_name": "Identity", "result_data_type": "numeric_single",
                "uom": "mg", "required": True, "release_blocking": True,
            }],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    spec_id = resp.json()["aggregate_id"]

    listing = await client.get(
        "/qc/v1/specifications", params={"q": "SPEC-MAT-OK"}, headers=auth_headers(op_token)
    )
    assert listing.status_code == 200
    items = listing.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == spec_id
    assert items[0]["scope_type"] == "material"
    assert items[0]["scope_version_id"] == str(matspec_id)

    # Backs /qc's redesigned "Test specifications" detail page (2026-09-26) -- no single-record GET
    # existed before this, only the list above.
    detail = await client.get(f"/qc/v1/specifications/{spec_id}", headers=auth_headers(op_token))
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert detail_body["id"] == spec_id
    assert detail_body["spec_code"] == "SPEC-MAT-OK"
    assert len(detail_body["test_definitions"]) == 1
    assert detail_body["test_definitions"][0]["test_code"] == "IDENTITY"


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

    readiness = await client.get(f"/qc/v1/release-readiness?sample_id={sample_id}", headers=auth_headers(admin_token))
    assert readiness.json()["ready"] is True

    record = await client.get(f"/qc/v1/samples/{sample_id}/record", headers=auth_headers(admin_token))
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


# ---------------------------------------------------------------------------
# QC-FR-011 (Task 4, 2026-09-23, SG-066): qc_analyst qualification gate on start_test_order, mirroring
# test_batch_execution.py::test_start_step_blocked_when_qualification_expired.
# ---------------------------------------------------------------------------


async def _order_ready_to_start(client, db, seeded, op_token, tag):
    async with db.begin():
        product_version = await _seed_product_version(db, seeded, code=f"QUAL-PROD-{tag}")
    spec_id = await _create_and_release_spec(client, op_token, product_version.id, code=f"QUAL-SPEC-{tag}")
    from app.modules.qc.models import QcTestDefinition

    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )
    sample_id = (
        await client.post(
            "/qc/v1/samples",
            json={
                "idempotency_key": idem(), "sample_number": f"QUAL-SAMPLE-{tag}", "sample_type": "finished_product",
                "source_type": "reserve",
            },
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    return (
        await client.post(
            "/qc/v1/test-orders",
            json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id},
            headers=auth_headers(op_token),
        )
    ).json()["aggregate_id"]


async def test_start_test_order_blocked_without_qc_analyst_qualification(client, seeded, db):
    """operator1 (the fixture's default) has a qc_analyst qualification seeded -- use a fresh Admin
    (qc_test_order.start is Admin-grantable too) with none at all."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.qualmissing")
    admin_token = await login(client, "admin.qualmissing")
    order_id = await _order_ready_to_start(client, db, seeded, admin_token, "missing")

    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "QUALIFICATION_MISSING"


async def test_start_test_order_blocked_with_expired_qc_analyst_qualification(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.qualexpired")
        admin = (await db.execute(select(User).where(User.username == "admin.qualexpired"))).scalar_one()
        db.add(Qualification(
            user_id=admin.id, qualification_code="qc_analyst",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        ))
    admin_token = await login(client, "admin.qualexpired")
    order_id = await _order_ready_to_start(client, db, seeded, admin_token, "expired")

    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "QUALIFICATION_EXPIRED"


async def test_qc_dashboard_and_export(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.qcdash")
    admin_token = await login(client, "admin.qcdash")
    order_id = await _order_ready_to_start(client, db, seeded, admin_token, "dash")

    dashboard = (await client.get("/qc/v1/dashboard", headers=auth_headers(admin_token))).json()
    assert dashboard["test_orders_by_state"].get("created", 0) >= 1
    assert "open_oos" in dashboard and "open_oot" in dashboard

    export = (await client.get("/qc/v1/export", headers=auth_headers(admin_token))).json()
    assert any(row["id"] == order_id for row in export)


# --- Client_Decisions_Neededanswers Topics 1/2 (SG-076 required-test half): release_material_lot now
# hard-blocks on a missing/unpassed required test, with an explicit supplier-COA-reliance bypass -------


async def _material_lot_with_required_test(client, db, seeded, admin_token, code_suffix):
    """Builds: Material -> released MaterialSpecificationVersion -> released material-scoped
    QcTestSpecification (one required+release_blocking IDENTITY test, acceptance_rule_business_id set)
    -> a receipt examined clean into a quarantine lot. Returns (lot_id, definition_id, sample_id)."""
    from tests.test_material_receipt_flow import _create_material, _create_receipt, _examine_clean

    rule_business_id = f"qc-acceptance:identity-{code_suffix}"
    await _author_and_release_rule(
        client, admin_token, db, rule_id=rule_business_id,
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )

    async with db.begin():
        material = Material(site_id=seeded["site_id"], code=f"RM-GATE-{code_suffix}", name="Gate Material", uom="kg")
        db.add(material)
        await db.flush()
        matspec = MaterialSpecificationVersion(
            material_spec_business_id=f"MATSPEC-GATE-{code_suffix}", version_no=1, material_id=material.id,
            name="Gate Material Spec", lifecycle_state="released", site_id=seeded["site_id"],
        )
        db.add(matspec)
        await db.flush()
        material_id = str(material.id)
        matspec_id = matspec.id

    spec_resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": f"SPEC-GATE-{code_suffix}", "scope_type": "material",
            "scope_version_id": str(matspec_id),
            "test_definitions": [{
                "test_code": "IDENTITY", "test_name": "Identity", "result_data_type": "numeric_single",
                "uom": "mg", "acceptance_rule_business_id": rule_business_id, "required": True, "release_blocking": True,
            }],
        },
        headers=auth_headers(admin_token),
    )
    assert spec_resp.status_code == 200, spec_resp.text
    spec_id = spec_resp.json()["aggregate_id"]
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
    definition_id = str(
        (await db.execute(select(QcTestDefinition.id).where(QcTestDefinition.specification_id == spec_id))).scalars().first()
    )

    receipt_id = await _create_receipt(client, admin_token, seeded["site_id"], material_id, receipt_number=f"RCPT-GATE-{code_suffix}")
    await _examine_clean(client, admin_token, receipt_id, internal_lot=f"LOT-GATE-{code_suffix}")
    lot = (await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == f"LOT-GATE-{code_suffix}"))).scalar_one()
    containers = (
        await db.execute(select(MaterialContainer).where(MaterialContainer.material_lot_id == lot.id))
    ).scalars().first()

    order_resp = await client.post(
        f"/materials/v1/lots/{lot.id}/sampling-orders",
        json={
            "idempotency_key": idem(), "lot_id": str(lot.id), "expected_version": 1,
            "selected_container_ids": [str(containers.id)],
            "assigned_sampler_user_id": str(seeded["users"]["qc.reviewer"].id),
        },
        headers=auth_headers(admin_token),
    )
    assert order_resp.status_code == 200, order_resp.text
    sampling_order_id = order_resp.json()["aggregate_id"]

    collect_resp = await client.post(
        f"/sampling-orders/{sampling_order_id}/collect",
        json={
            "idempotency_key": idem(), "sampling_order_id": sampling_order_id, "expected_version": 1,
            "sample_quantity": "1.000000", "sample_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert collect_resp.status_code == 200, collect_resp.text

    sample_id = str(
        (await db.execute(select(QcSample.id).where(QcSample.source_type == "material_lot", QcSample.source_id == lot.id)))
        .scalars().first()
    )
    return str(lot.id), definition_id, sample_id


async def _pass_required_test(client, sample_id, definition_id):
    """Operator (seeded with a qc_analyst qualification, same precedent as every other QC execution
    test in this file) performs the test; a QA Reviewer (independent, per SIG-FR-018) reviews it."""
    performer_token = await login(client, "operator1")
    reviewer_token = await login(client, "qa.reviewer")

    receive_resp = await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(performer_token),
    )
    assert receive_resp.status_code == 200, receive_resp.text

    order_resp = await client.post(
        "/qc/v1/test-orders",
        json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": definition_id},
        headers=auth_headers(performer_token),
    )
    assert order_resp.status_code == 200, order_resp.text
    order_id = order_resp.json()["aggregate_id"]

    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/start",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 1, "analyst_id": None},
        headers=auth_headers(performer_token),
    )
    assert resp.status_code == 200, resp.text

    raw_data_resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/raw-data",
        json={"idempotency_key": idem(), "test_order_id": order_id, "method_version": "HPLC-1"},
        headers=auth_headers(performer_token),
    )
    assert raw_data_resp.status_code == 200, raw_data_resp.text
    run_id = raw_data_resp.json()["aggregate_id"]

    result_resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/results",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "test_run_id": run_id,
            "result_type": "numeric_single", "value_decimal": "5.000000000000", "uom": "mg",
        },
        headers=auth_headers(performer_token),
    )
    assert result_resp.status_code == 200, result_resp.text

    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/complete",
        json={"idempotency_key": idem(), "test_order_id": order_id, "expected_version": 2},
        headers=auth_headers(performer_token),
    )
    assert resp.status_code == 200, resp.text

    challenge = (
        await client.post(
            f"/qc/v1/test-orders/{order_id}/signature-challenges", json={"action": "review"},
            headers=auth_headers(reviewer_token),
        )
    ).json()
    resp = await client.post(
        f"/qc/v1/test-orders/{order_id}/review",
        json={
            "idempotency_key": idem(), "test_order_id": order_id, "expected_version": 3,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 200, resp.text


async def _release_lot(client, db, token, lot_id, **overrides):
    """Always re-fetches the lot's current version -- sampling-order/collect steps bump it via the
    *app's* own session, so the test session's identity map must be expired first or `db.get()` would
    silently return a stale cached version from an earlier read in this same test."""
    db.expire_all()
    current = await db.get(MaterialLot, lot_id)
    current_version = current.version
    challenge = (
        await client.post(
            f"/material-lots/{lot_id}/signature-challenges", json={"action": "release"}, headers=auth_headers(token),
        )
    ).json()
    body = {
        "idempotency_key": idem(), "lot_id": lot_id, "expected_version": current_version,
        "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
    }
    body.update(overrides)
    return await client.post(f"/materials/v1/lots/{lot_id}/release", json=body, headers=auth_headers(token))


async def test_release_blocked_until_required_test_passes_then_succeeds(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.gate1")
    admin_token = await login(client, "admin.gate1")
    qa_token = await login(client, "qa.releaser")

    lot_id, definition_id, sample_id = await _material_lot_with_required_test(client, db, seeded, admin_token, "1")

    readiness = (await client.get(f"/materials/v1/lots/{lot_id}/release-readiness", headers=auth_headers(qa_token))).json()
    assert readiness["missing_required_tests"] == ["IDENTITY"]

    resp = await _release_lot(client, db, qa_token, lot_id)
    body = resp.json()
    assert resp.status_code == 409, resp.text
    assert body["code"] == "LOT_INELIGIBLE"
    assert body["details"]["missing_test_codes"] == ["IDENTITY"]

    await _pass_required_test(client, sample_id, definition_id)

    readiness = (await client.get(f"/materials/v1/lots/{lot_id}/release-readiness", headers=auth_headers(qa_token))).json()
    assert readiness["missing_required_tests"] == []

    resp = await _release_lot(client, db, qa_token, lot_id)
    assert resp.status_code == 200, resp.text

    db.expire_all()
    lot = await db.get(MaterialLot, lot_id)
    assert lot.status == "released"
    assert lot.coa_reliance is False


async def test_release_coa_reliance_requires_approved_supplier_and_coa_on_file(client, seeded, db):
    from app.modules.supplier_quality.models import Supplier

    async with db.begin():
        await _make_admin(db, seeded, "admin.gate2")
        # Approved up front so the receipt examines cleanly into a lot (the exam-time supplier check,
        # unrelated to this test) -- downgraded again below once the lot exists, to prove the
        # release-time check in _disposition_material_lot_v2 re-verifies independently rather than
        # trusting a stale approval from receipt time.
        supplier = Supplier(supplier_code="SUP-COA", legal_name="COA Supplier", role_type="supplier", status="approved")
        db.add(supplier)
        await db.flush()
        supplier_id = str(supplier.id)
    admin_token = await login(client, "admin.gate2")
    qa_token = await login(client, "qa.releaser")

    rule_business_id = "qc-acceptance:identity-coa"
    await _author_and_release_rule(
        client, admin_token, db, rule_id=rule_business_id,
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    async with db.begin():
        material = Material(site_id=seeded["site_id"], code="RM-GATE-COA", name="Gate COA Material", uom="kg")
        db.add(material)
        await db.flush()
        matspec = MaterialSpecificationVersion(
            material_spec_business_id="MATSPEC-GATE-COA", version_no=1, material_id=material.id,
            name="Gate COA Material Spec", lifecycle_state="released", site_id=seeded["site_id"],
        )
        db.add(matspec)
        await db.flush()
        material_id = str(material.id)
        matspec_id = matspec.id

    spec_resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": "SPEC-GATE-COA", "scope_type": "material",
            "scope_version_id": str(matspec_id),
            "test_definitions": [{
                "test_code": "IDENTITY", "test_name": "Identity", "result_data_type": "numeric_single",
                "uom": "mg", "acceptance_rule_business_id": rule_business_id, "required": True, "release_blocking": True,
            }],
        },
        headers=auth_headers(admin_token),
    )
    spec_id = spec_resp.json()["aggregate_id"]
    challenge = (
        await client.post(
            f"/qc/v1/specifications/{spec_id}/signature-challenges", json={"action": "release"},
            headers=auth_headers(admin_token),
        )
    ).json()
    await client.post(
        f"/qc/v1/specifications/{spec_id}/release",
        json={
            "idempotency_key": idem(), "specification_id": spec_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )

    receipt_resp = await client.post(
        "/materials/v1/receipts",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "receipt_number": "RCPT-GATE-COA",
            "material_id": material_id, "supplier_id": supplier_id,
            "received_gross_quantity": "100.000000", "accepted_quantity": "100.000000", "uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert receipt_resp.status_code == 200, receipt_resp.text
    receipt_id = receipt_resp.json()["aggregate_id"]
    examine_resp = await client.post(
        f"/materials/v1/receipts/{receipt_id}/examine",
        json={
            "idempotency_key": idem(), "receipt_id": receipt_id, "expected_version": 1,
            "labeling_ok": True, "shipping_damage_observed": False, "container_damage_observed": False, "seal_broken": False,
            "identity_confirmed": True, "internal_lot": "LOT-GATE-COA", "container_count": 1,
        },
        headers=auth_headers(admin_token),
    )
    assert examine_resp.status_code == 200, examine_resp.text
    lot = (await db.execute(select(MaterialLot).where(MaterialLot.internal_lot == "LOT-GATE-COA"))).scalar_one()
    lot_id = lot.id
    supplier_row = await db.get(Supplier, supplier_id)
    supplier_row.status = "draft"
    await db.commit()

    # Unapproved supplier: COA reliance refused even though a COA hash will be added below.
    resp = await _release_lot(client, db, qa_token, str(lot_id), coa_reliance=True, reason="Relying on supplier COA")
    assert resp.status_code == 422, resp.text
    assert "supplier" in resp.json()["message"].lower()

    supplier_row = await db.get(Supplier, supplier_id)
    supplier_row.status = "approved"
    await db.commit()

    # Approved supplier, but no COA document on file yet.
    resp = await _release_lot(client, db, qa_token, str(lot_id), coa_reliance=True, reason="Relying on supplier COA")
    assert resp.status_code == 422, resp.text
    assert "certificate" in resp.json()["message"].lower() or "coa" in resp.json()["message"].lower()

    receipt_row = await db.get(MaterialReceipt, receipt_id)
    receipt_row.coa_document_hash = "a" * 64
    await db.commit()

    # No reliance flag at all: still blocked by the missing required test, not released.
    resp = await _release_lot(client, db, qa_token, str(lot_id))
    assert resp.status_code == 409, resp.text

    # Approved supplier + COA on file + documented reason: succeeds.
    resp = await _release_lot(client, db, qa_token, str(lot_id), coa_reliance=True, reason="Supplier COA reviewed, meets specification")
    assert resp.status_code == 200, resp.text

    db.expire_all()
    released_lot = await db.get(MaterialLot, lot_id)
    assert released_lot.status == "released"
    assert released_lot.coa_reliance is True
    assert released_lot.coa_reliance_reason == "Supplier COA reviewed, meets specification"


async def test_create_test_order_with_external_provider(client, seeded, db):
    """Client gap-analysis Phase 6 (2026-10-05): a test order can record which Supplier (role_type
    "service_provider"/"both") performed it when sent to an external lab, and a report hash. A Supplier
    with the wrong role_type is rejected."""
    import uuid

    op_token = await login(client, "operator1")
    async with db.begin():
        provider = Supplier(supplier_code="SVC-QC-1", legal_name="Contract QC Labs Inc.", role_type="service_provider", status="approved")
        wrong_role_provider = Supplier(supplier_code="SUP-QC-WRONG-1", legal_name="Just A Supplier", role_type="supplier", status="approved")
        db.add_all([provider, wrong_role_provider])
        await db.flush()
        spec = QcTestSpecification(
            spec_code="SPEC-EXT-PROVIDER-1", version_no=1, scope_type="product",
            scope_version_id=uuid.uuid4(), status="released", version=1,
        )
        db.add(spec)
        await db.flush()
        definition = QcTestDefinition(
            specification_id=spec.id, test_code="ASSAY", test_name="Assay",
            result_data_type="numeric_single", required=True, release_blocking=True,
        )
        db.add(definition)
        await db.flush()
        definition_id, provider_id, wrong_role_provider_id = definition.id, provider.id, wrong_role_provider.id

    sample_resp = await client.post(
        "/qc/v1/samples",
        json={
            "idempotency_key": idem(), "sample_number": "SAMPLE-EXT-PROVIDER-1",
            "sample_type": "finished_product", "source_type": "reserve",
        },
        headers=auth_headers(op_token),
    )
    sample_id = sample_resp.json()["aggregate_id"]
    receive_resp = await client.post(
        f"/qc/v1/samples/{sample_id}/receive",
        json={"idempotency_key": idem(), "sample_id": sample_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    assert receive_resp.status_code == 200, receive_resp.text

    bad_resp = await client.post(
        "/qc/v1/test-orders",
        json={
            "idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": str(definition_id),
            "external_provider_id": str(wrong_role_provider_id),
        },
        headers=auth_headers(op_token),
    )
    assert bad_resp.status_code == 422, bad_resp.text
    assert bad_resp.json()["code"] == "VALIDATION_FAILED"

    good_resp = await client.post(
        "/qc/v1/test-orders",
        json={
            "idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": str(definition_id),
            "external_provider_id": str(provider_id), "external_report_hash": "abc123",
        },
        headers=auth_headers(op_token),
    )
    assert good_resp.status_code == 200, good_resp.text

    detail = await client.get(f"/qc/v1/samples/{sample_id}/record", headers=auth_headers(op_token))
    assert detail.status_code == 200, detail.text
    order = detail.json()["test_orders"][0]
    assert order["external_provider_id"] == str(provider_id)
    assert order["external_report_hash"] == "abc123"
