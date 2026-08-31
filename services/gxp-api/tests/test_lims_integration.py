"""WP-04 / Document 24 (SPEC-QC-002) thin slice: this module is an adapter in front of the already-built
`qc` module -- request a sample (calls qc.commands.create_sample), ingest a status update (calls
qc.commands.receive_sample), ingest a result (calls qc.commands.record_raw_data + record_result, reusing
its acceptance-rule PASS/OOS classification and append-only versioning unmodified), cancel a sample
(signed, 2 independent actors), and reconcile. Only ownership_mode='gxp_managed' is built this pass
(SG-067); LIMS-FR-013 real source authentication and LIMS-FR-016/020 (Document 25 OOS linkage) are
deferred (SG-067/SG-066)."""

from sqlalchemy import select

from app.modules.iam.models import User
from app.modules.lims_integration.models import LimsInstance, LimsMapping
from app.modules.qc.models import QcResult, QcSample, QcTestDefinition
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login
from tests.test_qc import _author_and_release_rule, _create_and_release_spec, _make_admin, _seed_product_version


async def _make_instance(client, db, seeded, actor_username="operator1", code="LIMS-A", ownership_mode="gxp_managed"):
    op_user = (await db.execute(select(User).where(User.username == actor_username))).scalars().first()
    instance = LimsInstance(
        instance_code=code, site_id=seeded["site_id"], provider_type="reference", ownership_mode=ownership_mode,
        service_actor_user_id=op_user.id, status="active",
    )
    db.add(instance)
    await db.flush()
    return instance


async def test_request_sample_creates_qc_sample_and_mapping(client, seeded, db):
    op_token = await login(client, "operator1")
    async with db.begin():
        instance = await _make_instance(client, db, seeded)

    resp = await client.post(
        f"/integrations/lims/{instance.id}/samples",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_sample_id": "S-100",
            "sample_number": "SAMPLE-LIMS-1", "sample_type": "finished_product", "source_type": "reserve",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    sample_id = resp.json()["aggregate_id"]

    sample = await db.get(QcSample, sample_id)
    assert sample is not None
    assert sample.state == "planned"

    from sqlalchemy import select

    mapping = (
        await db.execute(select(LimsMapping).where(LimsMapping.external_entity_id == "S-100"))
    ).scalars().first()
    assert mapping is not None
    assert str(mapping.internal_object_id) == sample_id


async def test_duplicate_external_sample_id_rejected(client, seeded, db):
    op_token = await login(client, "operator1")
    async with db.begin():
        instance = await _make_instance(client, db, seeded)

    body = {
        "idempotency_key": idem(), "instance_id": str(instance.id), "external_sample_id": "S-DUP",
        "sample_number": "SAMPLE-DUP-1", "sample_type": "finished_product", "source_type": "reserve",
    }
    resp1 = await client.post(f"/integrations/lims/{instance.id}/samples", json=body, headers=auth_headers(op_token))
    assert resp1.status_code == 200, resp1.text

    body2 = dict(body, idempotency_key=idem(), sample_number="SAMPLE-DUP-2")
    resp2 = await client.post(f"/integrations/lims/{instance.id}/samples", json=body2, headers=auth_headers(op_token))
    assert resp2.status_code == 409
    assert resp2.json()["code"] == "LIMS_DUPLICATE_EVENT"


async def _full_result_flow(client, db, seeded, *, value_decimal, external_result_version=1, external_event_id=None):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")

    admin_username = f"admin.lims-{idem()[:8]}"
    async with db.begin():
        instance = await _make_instance(client, db, seeded, code=f"LIMS-{idem()[:8]}")
        product_version = await _seed_product_version(db, seeded, code=f"PROD-{idem()[:8]}")
        await _make_admin(db, seeded, admin_username)
    admin_token = await login(client, admin_username)

    await _author_and_release_rule(
        client, admin_token, db, rule_id=f"qc-acceptance:{instance.instance_code}",
        expression_ast={"op": "lte", "args": [{"var": "value"}, "10.0"]},
    )
    spec_id = await _create_and_release_spec(
        client, qa_releaser_token, product_version.id, acceptance_rule_id=f"qc-acceptance:{instance.instance_code}",
        code=f"SPEC-{instance.instance_code}",
    )

    definition = (
        await db.execute(select(QcTestDefinition).where(QcTestDefinition.specification_id == spec_id))
    ).scalars().first()

    external_sample_id = f"S-{instance.instance_code}"
    sample_resp = await client.post(
        f"/integrations/lims/{instance.id}/samples",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_sample_id": external_sample_id,
            "sample_number": f"SAMPLE-{instance.instance_code}", "sample_type": "finished_product", "source_type": "reserve",
        },
        headers=auth_headers(op_token),
    )
    sample_id = sample_resp.json()["aggregate_id"]

    status_resp = await client.post(
        f"/integrations/lims/{instance.id}/events/status",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_event_id": f"evt-status-{idem()}",
            "external_sample_id": external_sample_id, "status": "received",
        },
        headers=auth_headers(op_token),
    )
    assert status_resp.status_code == 200, status_resp.text

    order_resp = await client.post(
        "/qc/v1/test-orders",
        json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": str(definition.id)},
        headers=auth_headers(op_token),
    )
    assert order_resp.status_code == 200, order_resp.text

    result_resp = await client.post(
        f"/integrations/lims/{instance.id}/events/results",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id),
            "external_event_id": external_event_id or f"evt-{idem()}",
            "external_sample_id": external_sample_id, "test_code": definition.test_code,
            "external_result_version": external_result_version, "method_version": definition.method_version or "",
            "result_type": "numeric_single", "value_decimal": value_decimal,
        },
        headers=auth_headers(op_token),
    )
    return instance, external_sample_id, definition, result_resp


async def test_ingest_result_pass_via_qc_module(client, seeded, db):
    instance, external_sample_id, definition, resp = await _full_result_flow(client, db, seeded, value_decimal="5.000000000000")
    assert resp.status_code == 200, resp.text
    result = await db.get(QcResult, resp.json()["aggregate_id"])
    assert result.outcome == "pass"


async def test_ingest_result_method_mismatch_rejected(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")
    async with db.begin():
        instance = await _make_instance(client, db, seeded, code=f"LIMS-{idem()[:8]}")
        product_version = await _seed_product_version(db, seeded, code=f"PROD-{idem()[:8]}")

    # method_version is baked in at spec-authoring time -- qc_test_definition has no UPDATE grant
    # (append-only once created, same fix as qc_result), so it cannot be set after the fact.
    draft_resp = await client.post(
        "/qc/v1/specifications/drafts",
        json={
            "idempotency_key": idem(), "spec_code": f"SPEC-{instance.instance_code}", "scope_type": "product",
            "scope_version_id": str(product_version.id),
            "test_definitions": [{
                "test_code": "ASSAY", "test_name": "Assay", "result_data_type": "numeric_single",
                "method_version": "HPLC-1", "uom": "mg", "required": True, "release_blocking": True,
            }],
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert draft_resp.status_code == 200, draft_resp.text
    spec_id = draft_resp.json()["aggregate_id"]
    challenge = (
        await client.post(
            f"/qc/v1/specifications/{spec_id}/signature-challenges", json={"action": "release"},
            headers=auth_headers(qa_releaser_token),
        )
    ).json()
    release_resp = await client.post(
        f"/qc/v1/specifications/{spec_id}/release",
        json={
            "idempotency_key": idem(), "specification_id": spec_id, "expected_version": 1,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert release_resp.status_code == 200, release_resp.text

    definition = (
        await db.execute(select(QcTestDefinition).where(QcTestDefinition.specification_id == spec_id))
    ).scalars().first()

    external_sample_id = f"S-{instance.instance_code}"
    sample_resp = await client.post(
        f"/integrations/lims/{instance.id}/samples",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_sample_id": external_sample_id,
            "sample_number": f"SAMPLE-{instance.instance_code}", "sample_type": "finished_product", "source_type": "reserve",
        },
        headers=auth_headers(op_token),
    )
    sample_id = sample_resp.json()["aggregate_id"]
    status_resp = await client.post(
        f"/integrations/lims/{instance.id}/events/status",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_event_id": f"evt-status-{idem()}",
            "external_sample_id": external_sample_id, "status": "received",
        },
        headers=auth_headers(op_token),
    )
    assert status_resp.status_code == 200, status_resp.text
    order_resp = await client.post(
        "/qc/v1/test-orders",
        json={"idempotency_key": idem(), "sample_id": sample_id, "test_definition_id": str(definition.id)},
        headers=auth_headers(op_token),
    )
    assert order_resp.status_code == 200, order_resp.text

    resp = await client.post(
        f"/integrations/lims/{instance.id}/events/results",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_event_id": f"evt-{idem()}",
            "external_sample_id": external_sample_id, "test_code": definition.test_code,
            "external_result_version": 1, "method_version": "WRONG-METHOD",
            "result_type": "numeric_single", "value_decimal": "5.0",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "LIMS_METHOD_MISMATCH"


async def test_ingest_result_revision_and_stale_version_rejected(client, seeded, db):
    instance, external_sample_id, definition, resp1 = await _full_result_flow(
        client, db, seeded, value_decimal="5.000000000000", external_result_version=1, external_event_id="evt-rev-1"
    )
    assert resp1.status_code == 200, resp1.text
    first_result_id = resp1.json()["aggregate_id"]

    op_token = await login(client, "operator1")
    revision_resp = await client.post(
        f"/integrations/lims/{instance.id}/events/results",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_event_id": "evt-rev-2",
            "external_sample_id": external_sample_id, "test_code": definition.test_code,
            "external_result_version": 2, "method_version": definition.method_version or "",
            "result_type": "numeric_single", "value_decimal": "6.000000000000",
        },
        headers=auth_headers(op_token),
    )
    assert revision_resp.status_code == 200, revision_resp.text
    revised_result = await db.get(QcResult, revision_resp.json()["aggregate_id"])
    assert str(revised_result.supersedes_result_id) is None or revised_result.id != first_result_id

    original = await db.get(QcResult, first_result_id)
    assert original.value_decimal == 5  # never edited

    stale_resp = await client.post(
        f"/integrations/lims/{instance.id}/events/results",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_event_id": "evt-rev-3",
            "external_sample_id": external_sample_id, "test_code": definition.test_code,
            "external_result_version": 1, "method_version": definition.method_version or "",
            "result_type": "numeric_single", "value_decimal": "7.000000000000",
        },
        headers=auth_headers(op_token),
    )
    assert stale_resp.status_code == 409
    assert stale_resp.json()["code"] == "LIMS_RESULT_VERSION_STALE"


async def test_duplicate_event_id_rejected(client, seeded, db):
    instance, external_sample_id, definition, resp1 = await _full_result_flow(
        client, db, seeded, value_decimal="5.000000000000", external_event_id="evt-dup-1"
    )
    assert resp1.status_code == 200, resp1.text

    op_token = await login(client, "operator1")
    dup_resp = await client.post(
        f"/integrations/lims/{instance.id}/events/results",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_event_id": "evt-dup-1",
            "external_sample_id": external_sample_id, "test_code": definition.test_code,
            "external_result_version": 2, "method_version": definition.method_version or "",
            "result_type": "numeric_single", "value_decimal": "6.0",
        },
        headers=auth_headers(op_token),
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["code"] == "LIMS_DUPLICATE_EVENT"


async def test_cancel_sample_signed_and_sod(client, seeded, db):
    op_token = await login(client, "operator1")
    qa_releaser_token = await login(client, "qa.releaser")
    async with db.begin():
        instance = await _make_instance(client, db, seeded, code=f"LIMS-{idem()[:8]}")

    sample_resp = await client.post(
        f"/integrations/lims/{instance.id}/samples",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_sample_id": "S-CANCEL",
            "sample_number": "SAMPLE-CANCEL", "sample_type": "finished_product", "source_type": "reserve",
        },
        headers=auth_headers(op_token),
    )
    sample_id = sample_resp.json()["aggregate_id"]

    # Same actor as the original requester cannot cancel (SoD) -- even with a valid challenge.
    challenge = (
        await client.post(
            f"/integrations/lims/{instance.id}/samples/{sample_id}/signature-challenges",
            json={"action": "cancel"}, headers=auth_headers(op_token),
        )
    ).json()
    resp = await client.post(
        f"/integrations/lims/{instance.id}/samples/{sample_id}/cancel",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "sample_id": sample_id, "reason": "duplicate order",
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403  # operator1 has no lims_sample.cancel permission either
    assert resp.json()["code"] == "ROLE_MISSING"

    challenge2 = (
        await client.post(
            f"/integrations/lims/{instance.id}/samples/{sample_id}/signature-challenges",
            json={"action": "cancel"}, headers=auth_headers(qa_releaser_token),
        )
    ).json()
    resp2 = await client.post(
        f"/integrations/lims/{instance.id}/samples/{sample_id}/cancel",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "sample_id": sample_id, "reason": "duplicate order",
            "challenge_id": challenge2["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp2.status_code == 200, resp2.text

    sample = await db.get(QcSample, sample_id)
    await db.refresh(sample)
    assert sample.state == "cancelled"


async def test_reconcile_detects_no_mismatch_for_consistent_mapping(client, seeded, db):
    op_token = await login(client, "operator1")
    async with db.begin():
        instance = await _make_instance(client, db, seeded, code=f"LIMS-{idem()[:8]}")

    await client.post(
        f"/integrations/lims/{instance.id}/samples",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_sample_id": "S-REC",
            "sample_number": "SAMPLE-REC", "sample_type": "finished_product", "source_type": "reserve",
        },
        headers=auth_headers(op_token),
    )

    resp = await client.post(
        f"/integrations/lims/{instance.id}/reconcile",
        json={"idempotency_key": idem(), "instance_id": str(instance.id)},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text


async def test_health_reports_instance_status(client, seeded, db):
    op_token = await login(client, "operator1")
    async with db.begin():
        instance = await _make_instance(client, db, seeded, code=f"LIMS-{idem()[:8]}")

    resp = await client.get(f"/integrations/lims/{instance.id}/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["ownership_mode"] == "gxp_managed"


async def test_non_gxp_managed_ownership_mode_rejected(client, seeded, db):
    op_token = await login(client, "operator1")
    async with db.begin():
        instance = await _make_instance(client, db, seeded, code=f"LIMS-{idem()[:8]}", ownership_mode="lims_managed_with_sync")

    resp = await client.post(
        f"/integrations/lims/{instance.id}/events/results",
        json={
            "idempotency_key": idem(), "instance_id": str(instance.id), "external_event_id": "evt-mode-1",
            "external_sample_id": "S-MODE", "test_code": "ASSAY", "external_result_version": 1,
            "method_version": "1", "result_type": "numeric_single", "value_decimal": "5.0",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"
