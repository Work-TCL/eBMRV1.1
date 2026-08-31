"""Document 47 (SPEC-EDGE-005) server-side "Integration Gateway": a released signal mapping (SG-127
signature) routes an already-accepted Document 43 `edge.edge_observations` row into a batch-context-bound
`MachineEvidenceCandidate` or a `MachineAlarmEvent`, never touching `batch`/`equipment` tables directly
(AG-05/AG-06) -- plus the command boundary's server-side half (SG-128 signed submit -> SG-129 unsigned
service-identity finalize) and the admin replay action (SG-131). The on-prem gateway runtime itself is out
of scope (plan-mode sign-off, `/root/.claude/plans/enumerated-swimming-dijkstra.md`); every call here is a
direct HTTP call against the server API, standing in for what a real gateway process would send.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from app.modules.machine_integration.models import MachineCommandProfile, MachineSource, SignalMapping
from app.modules.rules.models import UnitOfMeasure, UomConversion
from tests.conftest import auth_headers, idem, login
from tests.test_batch_flow import _create_and_issue_batch, _create_product_recipe
from tests.test_edge_flow import _enroll_gateway, _make_admin


async def _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-1"):
    async with db.begin():
        await _make_admin(db, seeded, username=f"admin.{fingerprint.lower()}")
    admin_token = await login(client, f"admin.{fingerprint.lower()}")

    resp = await _enroll_gateway(client, admin_token, seeded["site_id"], fingerprint=fingerprint)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    gateway_id = uuid.UUID(body["gateway_id"])
    bearer_token = body["bearer_token"]

    async with db.begin():
        source = MachineSource(
            site_id=seeded["site_id"], source_code=f"SRC-{fingerprint}", name="Filler PLC",
            gateway_id=gateway_id, protocol_connector="opcua",
        )
        db.add(source)
        await db.flush()
        source_id = source.id
    return gateway_id, bearer_token, source_id


async def _draft_mapping(
    db, seeded, source_id, *, mapping_key, evidence_class, batch_context_policy="NONE",
    drafted_by="integration.admin", native_type="Double", raw_unit=None, canonical_unit=None,
):
    async with db.begin():
        mapping = SignalMapping(
            site_id=seeded["site_id"], mapping_key=mapping_key, version=1, source_id=source_id,
            source_address="ns=4;s=Line1.Filler.Pressure", native_type=native_type, domain_code="FILL_PRESSURE",
            evidence_class=evidence_class, batch_context_policy=batch_context_policy,
            raw_unit=raw_unit, canonical_unit=canonical_unit,
            drafted_by_user_id=seeded["users"][drafted_by].id, lifecycle_state="draft",
        )
        db.add(mapping)
        await db.flush()
        mapping_id = mapping.id
    return mapping_id


async def _release_mapping(client, releaser_token, mapping_id, *, expected_version=1):
    challenge = (
        await client.post(
            "/machine-integration/v1/signal-mappings/signature-challenges",
            json={"mapping_id": str(mapping_id)}, headers=auth_headers(releaser_token),
        )
    ).json()
    return await client.post(
        f"/machine-integration/v1/signal-mappings/{mapping_id}/release",
        json={
            "idempotency_key": idem(), "mapping_id": str(mapping_id), "expected_version": expected_version,
            "reason": "Commissioning complete, test vectors pass", "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(releaser_token),
    )


async def _post_observation(
    client, bearer_token, gateway_id, *, mapping_key, quality="GOOD", raw=None, expected_version=1, gateway_sequence=1,
):
    event_id = uuid.uuid4()
    resp = await client.post(
        f"/edge/v1/gateways/{gateway_id}/observations:batch",
        json={
            "idempotency_key": idem(), "expected_version": expected_version,
            "observations": [{
                "event_id": str(event_id), "gateway_sequence": gateway_sequence, "mapping_id": mapping_key,
                "mapping_version": "1", "quality": quality, "raw": raw or {"value": 12.3},
                "normalized": raw or {"value": 12.3},
            }],
        },
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    return event_id, resp


async def test_release_mapping_then_ingest_creates_step_result_candidate(client, seeded, db):
    releaser_token = await login(client, "qa.releaser")

    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded)
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="FILL_PRESSURE_V1", evidence_class="STEP_RESULT", batch_context_policy="NONE",
    )

    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"]

    event_id, obs_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="FILL_PRESSURE_V1")
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert body["candidates_created"] == [] or len(body["candidates_created"]) == 1
    assert len(body["candidates_created"]) == 1
    assert body["rejected"] == []
    assert body["resulting_version"] == 2


async def test_release_signature_rejects_drafting_actor_as_signer(client, seeded, db):
    releaser_token = await login(client, "qa.releaser")
    gateway_id, _, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-SOD")
    # Drafted by the same QA Releaser who will attempt to release it -- holds the required permission
    # (unlike "integration.admin", which would be rejected at the RBAC layer before independence is ever
    # checked), so this actually exercises the SG-127 SoD independence check itself.
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="SOD_TEST", evidence_class="STEP_RESULT", drafted_by="qa.releaser",
    )

    challenge = (
        await client.post(
            "/machine-integration/v1/signal-mappings/signature-challenges",
            json={"mapping_id": str(mapping_id)}, headers=auth_headers(releaser_token),
        )
    ).json()
    resp = await client.post(
        f"/machine-integration/v1/signal-mappings/{mapping_id}/release",
        json={
            "idempotency_key": idem(), "mapping_id": str(mapping_id), "expected_version": 1,
            "reason": "attempting self-release", "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_ambiguous_batch_context_blocks_step_result(client, seeded, db):
    releaser_token = await login(client, "qa.releaser")
    op_token = await login(client, "operator1")

    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-CTX")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="CTX_TEST", evidence_class="STEP_RESULT", batch_context_policy="REQUIRED",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    product_id, recipe_id = await _create_product_recipe(client, op_token, seeded["site_id"])
    batch_id_1 = await _create_and_issue_batch(client, op_token, seeded["site_id"], product_id, recipe_id, "MI-B1")
    batch_id_2 = await _create_and_issue_batch(client, op_token, seeded["site_id"], product_id, recipe_id, "MI-B2")

    for batch_id in (batch_id_1, batch_id_2):
        resp = await client.post(
            "/machine-integration/v1/batch-contexts",
            json={"idempotency_key": idem(), "source_id": str(source_id), "batch_id": batch_id},
            headers=auth_headers(op_token),
        )
        assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="CTX_TEST")
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert body["candidates_created"] == []
    assert body["rejected"] == [{"event_id": str(event_id), "code": "BATCH_CONTEXT_AMBIGUOUS"}]


async def test_alarm_ingestion_creates_alarm_event_not_hold(client, seeded, db):
    from sqlalchemy import select

    from app.modules.equipment.models import EquipmentAsset
    from app.modules.machine_integration.models import MachineAlarmEvent

    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-ALARM")
    mapping_id = await _draft_mapping(db, seeded, source_id, mapping_key="ALARM_TEST", evidence_class="ALARM")
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="ALARM_TEST", raw={"alarm_code": "E-STOP", "severity": "CRITICAL"},
    )
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert len(body["alarms_created"]) == 1

    alarm = await db.get(MachineAlarmEvent, uuid.UUID(body["alarms_created"][0]))
    assert alarm.severity == "CRITICAL"
    assert alarm.review_status == "PENDING_REVIEW"
    # SG-130 boundary: no equipment_asset row was created or held as a side effect of this alarm.
    assert (await db.execute(select(EquipmentAsset))).scalars().first() is None


async def test_submit_and_finalize_machine_command(client, seeded, db):
    equip_token = await login(client, "equipment.admin")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-CMD")

    async with db.begin():
        profile = MachineCommandProfile(
            site_id=seeded["site_id"], operation_code="RESET_COUNTER", version=1, lifecycle_state="released",
            allowed_batch_states=None, timeout_ms=30000, requires_readback=True,
        )
        db.add(profile)
        await db.flush()

    challenge = (
        await client.post(
            "/machine-integration/v1/machine-commands/signature-challenges",
            json={"source_id": str(source_id), "operation_code": "RESET_COUNTER", "parameters": {}},
            headers=auth_headers(equip_token),
        )
    ).json()
    submit_resp = await client.post(
        "/machine-integration/v1/machine-commands",
        json={
            "idempotency_key": idem(), "source_id": str(source_id), "operation_code": "RESET_COUNTER",
            "parameters": {}, "reason": "Reset filler counter after changeover",
            "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(equip_token),
    )
    assert submit_resp.status_code == 200, submit_resp.text
    request_id = submit_resp.json()["aggregate_id"]
    assert submit_resp.json()["signature_id"]

    finalize_resp = await client.post(
        f"/machine-integration/v1/machine-commands/{request_id}/finalize",
        json={"idempotency_key": idem(), "expected_version": 1, "outcome_status": "COMPLETED", "native_response": {"ack": True}},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert finalize_resp.status_code == 200, finalize_resp.text

    detail = (await client.get(f"/machine-integration/v1/machine-commands/{request_id}")).json()
    assert detail["status"] == "COMPLETED"


async def test_submit_machine_command_without_released_profile_rejected(client, seeded, db):
    equip_token = await login(client, "equipment.admin")
    _, _, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-NOPROFILE")

    challenge = (
        await client.post(
            "/machine-integration/v1/machine-commands/signature-challenges",
            json={"source_id": str(source_id), "operation_code": "UNKNOWN_OP", "parameters": {}},
            headers=auth_headers(equip_token),
        )
    ).json()
    resp = await client.post(
        "/machine-integration/v1/machine-commands",
        json={
            "idempotency_key": idem(), "source_id": str(source_id), "operation_code": "UNKNOWN_OP",
            "parameters": {}, "reason": "no profile exists", "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(equip_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "COMMAND_NOT_ALLOWED"


async def test_replay_historical_evidence_signed(client, seeded, db):
    admin_token = await login(client, "integration.admin")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-REPLAY")
    event_id, obs_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="UNMAPPED")
    assert obs_resp.status_code == 200, obs_resp.text

    challenge = (
        await client.post(
            "/machine-integration/v1/evidence-replays/signature-challenges",
            json={"event_ids": [str(event_id)], "mode": "REPLAY"}, headers=auth_headers(admin_token),
        )
    ).json()
    resp = await client.post(
        f"/machine-integration/v1/sites/{seeded['site_id']}/evidence-replays",
        json={
            "idempotency_key": idem(), "event_ids": [str(event_id)], "mode": "REPLAY",
            "reason": "Mapping was fixed after initial rejection, replay original evidence",
            "challenge_id": challenge["challenge_id"], "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"]


async def test_unauthorized_ingest_without_service_token_rejected(client, seeded, db):
    _, _, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-UNAUTH")
    resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": []},
    )
    assert resp.status_code == 401


async def test_stale_version_on_ingest_rejected(client, seeded, db):
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-STALE")
    resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 99, "event_ids": []},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-DUP")
    key = idem()
    body = {"idempotency_key": key, "expected_version": 1, "event_ids": []}
    first = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest", json=body,
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    second = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest", json=body,
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["command_id"] == second.json()["command_id"]


async def test_single_open_context_binds_candidate_and_reclose_rejected(client, seeded, db):
    releaser_token = await login(client, "qa.releaser")
    op_token = await login(client, "operator1")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-CTX2")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="CTX2_TEST", evidence_class="STEP_RESULT", batch_context_policy="REQUIRED",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    product_id, recipe_id = await _create_product_recipe(client, op_token, seeded["site_id"])
    batch_id = await _create_and_issue_batch(client, op_token, seeded["site_id"], product_id, recipe_id, "MI-CTX2-B1")
    open_resp = await client.post(
        "/machine-integration/v1/batch-contexts",
        json={"idempotency_key": idem(), "source_id": str(source_id), "batch_id": batch_id},
        headers=auth_headers(op_token),
    )
    assert open_resp.status_code == 200, open_resp.text
    context_id = open_resp.json()["context_id"]

    event_id, obs_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="CTX2_TEST")
    assert obs_resp.status_code == 200, obs_resp.text
    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert len(body["candidates_created"]) == 1
    from app.modules.machine_integration.models import MachineEvidenceCandidate

    candidate = await db.get(MachineEvidenceCandidate, uuid.UUID(body["candidates_created"][0]))
    assert str(candidate.batch_context_id) == context_id

    close_resp = await client.post(
        f"/machine-integration/v1/batch-contexts/{context_id}/close",
        json={"idempotency_key": idem(), "context_id": context_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    assert close_resp.status_code == 200, close_resp.text

    reclose_resp = await client.post(
        f"/machine-integration/v1/batch-contexts/{context_id}/close",
        json={"idempotency_key": idem(), "context_id": context_id, "expected_version": 2},
        headers=auth_headers(op_token),
    )
    assert reclose_resp.status_code == 409, reclose_resp.text
    assert reclose_resp.json()["code"] == "INVALID_TRANSITION"


async def test_build_cycle_evidence_manifest(client, seeded, db):
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-CYCLE")
    event_id, obs_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="CYCLE_RAW", raw={"value": 5.0})
    assert obs_resp.status_code == 200, obs_resp.text

    resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/cycle-evidence-manifests",
        json={
            "idempotency_key": idem(), "expected_version": 1, "cycle_id": "CYCLE-0001",
            "event_ids": [str(event_id)], "statistics": {"min": 4.8, "max": 5.2, "avg": 5.0},
        },
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["manifest_id"]
    assert body["manifest_hash"]


async def test_ingest_type_mismatch_rejected_no_implicit_cast(client, seeded, db):
    """MAP-FR-004: native_type="Double" (numeric family) with a non-numeric raw value is rejected, not
    silently coerced -- "no implicit casts" is the acceptance intent."""
    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-TYPE")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="TYPE_MISMATCH", evidence_class="STEP_RESULT", batch_context_policy="NONE",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="TYPE_MISMATCH", raw={"value": "not-a-number"},
    )
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert body["candidates_created"] == []
    assert body["rejected"] == [{"event_id": str(event_id), "code": "TYPE_VALIDATION_FAILED"}]


async def test_ingest_null_value_not_type_validated_or_converted(client, seeded, db):
    """MAP-FR-004: a missing/null `value` is left as-is -- Document 47 does not define an accept/reject
    policy for "no reading", and this pass does not invent one."""
    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-NULL")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="NULL_VALUE", evidence_class="STEP_RESULT", batch_context_policy="NONE",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="NULL_VALUE", raw={"value": None},
    )
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert body["rejected"] == []
    assert len(body["candidates_created"]) == 1


async def test_ingest_applies_released_uom_conversion(client, seeded, db):
    """MAP-FR-005/006: a released `gxp_uom_conversion` row converts the raw reading into the mapping's
    canonical unit using the released factor, retaining the raw reading/unit unchanged alongside it --
    the same Document 110 `resolve_uom`/`resolve_conversion` + `Decimal(str(value)) * factor` mechanism
    `app.modules.rules.commands._apply_unit_policy` already uses for rule inputs."""
    async with db.begin():
        db.add(UnitOfMeasure(code="psi-mi1", dimension="PRESSURE", base_unit="psi-mi1", factor=Decimal("1"), precision_dp=4, status="released"))
        db.add(UnitOfMeasure(code="bar-mi1", dimension="PRESSURE", base_unit="psi-mi1", factor=Decimal("14.5038"), precision_dp=4, status="released"))
        db.add(
            UomConversion(
                from_code="psi-mi1", to_code="bar-mi1", factor=Decimal("0.0689476"), rounding_stage="none",
                effective_from=datetime.now(timezone.utc), status="released",
            )
        )

    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-UOM")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="PRESSURE_CONV", evidence_class="STEP_RESULT", batch_context_policy="NONE",
        raw_unit="psi-mi1", canonical_unit="bar-mi1",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="PRESSURE_CONV", raw={"value": 100},
    )
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert body["rejected"] == []
    assert len(body["candidates_created"]) == 1

    from app.modules.machine_integration.models import MachineEvidenceCandidate

    candidate = await db.get(MachineEvidenceCandidate, uuid.UUID(body["candidates_created"][0]))
    assert candidate.value["value"] == 100  # raw reading retained, not overwritten
    # Numeric equality, not string equality: the stored factor round-trips through the DB's
    # Numeric(38,18) column, which carries more trailing zero precision than a bare Python literal --
    # same non-issue app.modules.rules.commands._apply_unit_policy's own str(Decimal(...) * factor)
    # pattern has (nothing in this codebase asserts on that string's exact scale either).
    assert Decimal(candidate.value["canonical_value"]) == Decimal("100") * Decimal("0.0689476")
    assert candidate.value["canonical_unit"] == "bar-mi1"


async def test_ingest_unresolvable_conversion_rejected(client, seeded, db):
    """MAP-FR-005/006: raw_unit/canonical_unit both resolve as released UOM codes but no released
    conversion row links them -- fails closed (UOM_CONVERSION_UNAVAILABLE), never guesses a factor."""
    async with db.begin():
        db.add(UnitOfMeasure(code="degc-mi2", dimension="TEMPERATURE", base_unit="degc-mi2", factor=Decimal("1"), precision_dp=4, status="released"))
        db.add(UnitOfMeasure(code="degf-mi2", dimension="TEMPERATURE", base_unit="degc-mi2", factor=Decimal("1"), precision_dp=4, status="released"))

    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-NOCONV")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="TEMP_NOCONV", evidence_class="STEP_RESULT", batch_context_policy="NONE",
        raw_unit="degc-mi2", canonical_unit="degf-mi2",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="TEMP_NOCONV", raw={"value": 20},
    )
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert body["candidates_created"] == []
    assert body["rejected"] == [{"event_id": str(event_id), "code": "UOM_CONVERSION_UNAVAILABLE"}]


async def test_ingest_alarm_class_never_type_validated(client, seeded, db):
    """MAP-FR-004 scoping: ALARM-class evidence has no `value` field at all (alarm_code/severity
    instead) -- type/unit validation must not run against it. Regression guard for the
    CANDIDATE_EVIDENCE_CLASSES-only wiring."""
    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-ALM2")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="ALARM_TYPE_TEST", evidence_class="ALARM", batch_context_policy="NONE",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="ALARM_TYPE_TEST",
        raw={"alarm_code": "E-STOP", "severity": "CRITICAL"},
    )
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert body["rejected"] == []
    assert len(body["alarms_created"]) == 1


async def test_evidence_review_lists_candidate_and_alarm(client, seeded, db):
    """MAP-FR-030: a QA Reviewer can see an unreviewed candidate and a pending alarm through the
    read-only review-visibility endpoint; an unauthorized role (Operator) is denied."""
    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-REV")

    candidate_mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="REVIEW_CANDIDATE", evidence_class="STEP_RESULT", batch_context_policy="NONE",
    )
    assert (await _release_mapping(client, releaser_token, candidate_mapping_id)).status_code == 200
    alarm_mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="REVIEW_ALARM", evidence_class="ALARM", batch_context_policy="NONE",
    )
    assert (await _release_mapping(client, releaser_token, alarm_mapping_id, expected_version=1)).status_code == 200

    cand_event_id, cand_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="REVIEW_CANDIDATE")
    assert cand_resp.status_code == 200, cand_resp.text
    alarm_event_id, alarm_resp = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="REVIEW_ALARM", raw={"alarm_code": "E-STOP", "severity": "CRITICAL"},
        expected_version=2, gateway_sequence=2,
    )
    assert alarm_resp.status_code == 200, alarm_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(cand_event_id), str(alarm_event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text

    reviewer_token = await login(client, "qa.reviewer")
    review_resp = await client.get(
        f"/machine-integration/v1/evidence-review?site_id={seeded['site_id']}", headers=auth_headers(reviewer_token),
    )
    assert review_resp.status_code == 200, review_resp.text
    body = review_resp.json()
    assert str(cand_event_id) in {c["event_id"] for c in body["candidates"]}
    assert str(alarm_event_id) in {a["event_id"] for a in body["alarms"]}

    op_token = await login(client, "operator1")
    denied_resp = await client.get(
        f"/machine-integration/v1/evidence-review?site_id={seeded['site_id']}", headers=auth_headers(op_token),
    )
    assert denied_resp.status_code == 403, denied_resp.text


# ---------------------------------------------------------------------------
# SG-127/SG-129 follow-up: MAP-FR-011/017/024/025/027/031.
# ---------------------------------------------------------------------------


async def test_ingest_preserves_setpoint_and_actual_separately(client, seeded, db):
    """MAP-FR-017: setpoint and measured actual survive as distinct keys in the resulting candidate's
    value -- ingest_machine_evidence() passes the observation payload through verbatim (dict(payload)),
    never merging or dropping either."""
    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-SP")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="SETPOINT_ACTUAL", evidence_class="STEP_RESULT", batch_context_policy="NONE",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="SETPOINT_ACTUAL", raw={"setpoint": 100, "actual": 98.5},
    )
    assert obs_resp.status_code == 200, obs_resp.text

    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    body = ingest_resp.json()
    assert body["rejected"] == []

    from app.modules.machine_integration.models import MachineEvidenceCandidate

    candidate = await db.get(MachineEvidenceCandidate, uuid.UUID(body["candidates_created"][0]))
    assert candidate.value["setpoint"] == 100
    assert candidate.value["actual"] == 98.5


async def test_cycle_evidence_manifest_window_can_span_beyond_cycle_bounds(client, seeded, db):
    """MAP-FR-025: buildCycleEvidenceManifest() never filters event_ids by timestamp against
    cycle_start/cycle_end -- a caller may include pre/during/post-cycle observations in one manifest to
    capture a full evidence window, not just what falls strictly inside the cycle timeframe."""
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-WIN")

    pre_event_id, pre_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="ANY", gateway_sequence=1, expected_version=1)
    assert pre_resp.status_code == 200, pre_resp.text
    during_event_id, during_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="ANY", gateway_sequence=2, expected_version=2)
    assert during_resp.status_code == 200, during_resp.text
    post_event_id, post_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="ANY", gateway_sequence=3, expected_version=3)
    assert post_resp.status_code == 200, post_resp.text

    cycle_moment = datetime.now(timezone.utc)
    manifest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/cycle-evidence-manifests",
        json={
            "idempotency_key": idem(), "expected_version": 1, "cycle_id": "CYCLE-WINDOW-1",
            "event_ids": [str(pre_event_id), str(during_event_id), str(post_event_id)],
            "cycle_start": cycle_moment.isoformat(), "cycle_end": cycle_moment.isoformat(),
        },
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert manifest_resp.status_code == 200, manifest_resp.text

    from app.modules.machine_integration.models import CycleEvidenceManifest

    manifest = await db.get(CycleEvidenceManifest, uuid.UUID(manifest_resp.json()["manifest_id"]))
    assert set(manifest.event_ids) == {str(pre_event_id), str(during_event_id), str(post_event_id)}


async def test_open_batch_context_pins_mapping_version_for_life_of_context(client, seeded, db):
    """MAP-FR-027: an OPEN batch context keeps using the mapping version it first routed evidence with,
    even after a newer version of the same mapping_key is released mid-batch -- "open batches keep issued
    mapping version", not silently upgraded to the latest release."""
    releaser_token = await login(client, "qa.releaser")
    op_token = await login(client, "operator1")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-PIN")

    v1_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="PIN_TEST", evidence_class="STEP_RESULT", batch_context_policy="REQUIRED",
    )
    resp = await _release_mapping(client, releaser_token, v1_id, expected_version=1)
    assert resp.status_code == 200, resp.text

    product_id, recipe_id = await _create_product_recipe(client, op_token, seeded["site_id"])
    batch_id = await _create_and_issue_batch(client, op_token, seeded["site_id"], product_id, recipe_id, "MI-PIN-B1")
    open_resp = await client.post(
        "/machine-integration/v1/batch-contexts",
        json={"idempotency_key": idem(), "source_id": str(source_id), "batch_id": batch_id},
        headers=auth_headers(op_token),
    )
    assert open_resp.status_code == 200, open_resp.text
    context_id = open_resp.json()["context_id"]

    event_id_1, obs_resp_1 = await _post_observation(client, bearer_token, gateway_id, mapping_key="PIN_TEST", gateway_sequence=1)
    assert obs_resp_1.status_code == 200, obs_resp_1.text
    ingest_resp_1 = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id_1)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp_1.status_code == 200, ingest_resp_1.text
    assert len(ingest_resp_1.json()["candidates_created"]) == 1

    from app.modules.machine_integration.models import BatchContext, MachineEvidenceCandidate, SignalMapping

    # Read + draft-and-release v2 combined into one transaction -- a bare db.get() followed later by a
    # separate `async with db.begin():` leaves the session's autobegun transaction open and collides
    # ("A transaction is already begun on this Session").
    async with db.begin():
        context = await db.get(BatchContext, uuid.UUID(context_id))
        assert context.mapping_id == v1_id

        # Draft v2 of the SAME mapping_key while the batch context is still open.
        v2 = SignalMapping(
            site_id=seeded["site_id"], mapping_key="PIN_TEST", version=2, source_id=source_id,
            source_address="ns=4;s=Line1.Filler.Pressure.v2", native_type="Double", domain_code="FILL_PRESSURE_V2",
            evidence_class="STEP_RESULT", batch_context_policy="REQUIRED",
            drafted_by_user_id=seeded["users"]["integration.admin"].id, lifecycle_state="draft",
        )
        db.add(v2)
        await db.flush()
        v2_id = v2.id
    resp = await _release_mapping(client, releaser_token, v2_id, expected_version=1)
    assert resp.status_code == 200, resp.text

    # Second ingest for the SAME open context must still use v1 (pinned), not the newly released v2.
    event_id_2, obs_resp_2 = await _post_observation(
        client, bearer_token, gateway_id, mapping_key="PIN_TEST", gateway_sequence=2, expected_version=2,
    )
    assert obs_resp_2.status_code == 200, obs_resp_2.text
    ingest_resp_2 = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 2, "event_ids": [str(event_id_2)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp_2.status_code == 200, ingest_resp_2.text
    assert len(ingest_resp_2.json()["candidates_created"]) == 1
    candidate_2 = await db.get(MachineEvidenceCandidate, uuid.UUID(ingest_resp_2.json()["candidates_created"][0]))
    assert candidate_2.mapping_id == v1_id
    assert candidate_2.domain_code == "FILL_PRESSURE"  # v1's domain_code, not v2's "FILL_PRESSURE_V2"


async def test_get_machine_evidence_export_composes_manifest_and_candidates(client, seeded, db):
    """MAP-FR-031: the inspection export composes an already-built cycle evidence manifest with the
    candidates/alarms whose event_ids it covers, plus its hash/reference fields."""
    releaser_token = await login(client, "qa.releaser")
    gateway_id, bearer_token, source_id = await _enrolled_gateway_and_source(client, db, seeded, fingerprint="MI-GW-EXPORT")
    mapping_id = await _draft_mapping(
        db, seeded, source_id, mapping_key="EXPORT_TEST", evidence_class="STEP_RESULT", batch_context_policy="NONE",
    )
    resp = await _release_mapping(client, releaser_token, mapping_id)
    assert resp.status_code == 200, resp.text

    event_id, obs_resp = await _post_observation(client, bearer_token, gateway_id, mapping_key="EXPORT_TEST", raw={"value": 42})
    assert obs_resp.status_code == 200, obs_resp.text
    ingest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/evidence:ingest",
        json={"idempotency_key": idem(), "expected_version": 1, "event_ids": [str(event_id)]},
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert ingest_resp.status_code == 200, ingest_resp.text
    candidate_id = ingest_resp.json()["candidates_created"][0]

    manifest_resp = await client.post(
        f"/machine-integration/v1/machine-sources/{source_id}/cycle-evidence-manifests",
        json={
            "idempotency_key": idem(), "expected_version": 2, "cycle_id": "CYCLE-EXPORT-1",
            "event_ids": [str(event_id)], "raw_evidence_ref": "s3://evidence/cycle-export-1.csv",
            "historian_instance_ref": "historian-plant-1", "aggregation_rule_ref": "AGG-RULE-001",
        },
        headers={"Authorization": f"Bearer {bearer_token}"},
    )
    assert manifest_resp.status_code == 200, manifest_resp.text
    manifest_id = manifest_resp.json()["manifest_id"]

    qa_token = await login(client, "qa.reviewer")
    export_resp = await client.get(
        f"/machine-integration/v1/cycle-evidence-manifests/{manifest_id}/export", headers=auth_headers(qa_token),
    )
    assert export_resp.status_code == 200, export_resp.text
    body = export_resp.json()
    assert body["manifest_hash"]
    assert body["raw_evidence_ref"] == "s3://evidence/cycle-export-1.csv"
    assert body["historian_instance_ref"] == "historian-plant-1"
    assert body["aggregation_rule_ref"] == "AGG-RULE-001"
    assert body["candidates"][0]["id"] == candidate_id

    op_token = await login(client, "operator1")
    denied_resp = await client.get(
        f"/machine-integration/v1/cycle-evidence-manifests/{manifest_id}/export", headers=auth_headers(op_token),
    )
    assert denied_resp.status_code == 403, denied_resp.text
