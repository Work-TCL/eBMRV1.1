"""Document 26 (SPEC-QMS-001) -- the buildable slice: the linear OPEN -> TRIAGE -> CONTAINMENT ->
INVESTIGATION -> IMPACT_ASSESSMENT -> DISPOSITION -> CLOSED pipeline plus CLOSED -> REOPENED, matching the
module's own 9-op API list exactly. New module. DEV-FR-002/014/015/016(partial)/021/022/023/024 are out of
scope this pass -- see docs/generated/18_SPEC_GAPS.md SG-059..SG-062.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username):
    user = User(
        username=username, email=f"{username}@example.com", full_name="Test Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


async def _setup(db, seeded, tag, *, signed=False):
    """Creates an admin user (and, when signed=True, a real signature_required policy for disposition/
    close -- otherwise both are left signature_required=False, matching test_release.py's precedent for
    modules not under signature-specific test)."""
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.dev{tag}")
        db.add(SignaturePolicy(record_type="deviation_record", action="disposition", meaning="Approved", signature_required=signed))
        db.add(SignaturePolicy(record_type="deviation_record", action="close", meaning="Approved", signature_required=signed))
    return owner


def _create_body(site_id, owner_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "deviation_number": f"DEV-{uuid.uuid4().hex[:8]}",
        "deviation_type": "process", "source_type": "batch", "source_id": str(uuid.uuid4()), "severity": "major",
        "owner_subject_id": str(owner_id),
    }
    body.update(overrides)
    return body


async def _create(client, token, site_id, owner_id, **overrides):
    resp = await client.post("/qms/v1/deviations", json=_create_body(site_id, owner_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _advance_to_disposition(client, token, deviation_id, *, investigator_id):
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/triage",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 1, "severity": "major", "investigation_priority": "high"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/contain",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 2, "containment": {"actions": [{"target_type": "batch", "target_id": str(uuid.uuid4()), "description": "batch quarantined"}]}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/investigation",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 3,
            "investigator_subject_id": str(investigator_id), "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "root_cause": {"method": "5-why", "no_assignable_cause": False},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/impact",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 4,
            "impact_assessment": {k: "none" for k in (
                "quality_impact", "patient_user_impact", "released_distributed_product_impact",
                "validation_impact", "data_integrity_impact", "regulatory_impact",
            )},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return 5  # next expected_version


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/deviations", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_rejects_unrecognized_source_type(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.dev1")
    resp = await client.post(
        "/qms/v1/deviations", json=_create_body(seeded["site_id"], owner.id, source_type="not_a_real_source"), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "DEVIATION_SOURCE_INVALID"


async def test_create_requires_deviation_number_unique(client, seeded, db):
    owner = await _setup(db, seeded, "2")
    token = await login(client, "admin.dev2")
    body = _create_body(seeded["site_id"], owner.id, deviation_number="DEV-DUP-1")
    resp1 = await client.post("/qms/v1/deviations", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    body2 = _create_body(seeded["site_id"], owner.id, deviation_number="DEV-DUP-1")
    resp2 = await client.post("/qms/v1/deviations", json=body2, headers=auth_headers(token))
    assert resp2.status_code == 422, resp2.text
    assert resp2.json()["code"] == "VALIDATION_FAILED"


async def test_full_lifecycle_to_closed(client, seeded, db):
    """Document 26's own 9-op API list has no signature-challenge endpoint (unlike the original WP-01/02
    kernel modules' `POST .../signature-challenges`), and disposition/close's signature policy is a
    still-open baseline gap (docs/generated/11_SIGNATURE_POLICY_MAP.md: SG-004) -- so, like release_scope
    and qa_review_package before it, this pipeline is exercised with signature_required=False. The
    signature ceremony *mechanism* itself (MISSING_SIGNATURE / SIGNATURE_POLICY_UNRESOLVED fail-closed) is
    covered separately below.
    """
    owner = await _setup(db, seeded, "3", signed=False)
    token = await login(client, "admin.dev3")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact found", "capa_required": True,
            "capa_rationale": "recurring pattern across 3 batches this quarter -- systemic action warranted",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is None
    next_version += 1

    from sqlalchemy import select as sa_select
    from app.modules.mutation.models import OutboxEvent
    capa_events = (
        await db.execute(
            sa_select(OutboxEvent).where(OutboxEvent.aggregate_id == uuid.UUID(deviation_id), OutboxEvent.event_type == "DeviationCAPARequired")
        )
    ).scalars().all()
    assert len(capa_events) == 1

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/close",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version, "conclusion": ""},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "QA_CLOSURE_REQUIRED"

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/close",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "conclusion": "Investigated; no quality impact; disposition CONTINUE.",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_disposition_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "18", signed=True)
    token = await login(client, "admin.dev18")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact found", "capa_required": False,
            "capa_rationale": "isolated event, no systemic pattern",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_close_blocked_before_containment_investigation_impact_disposition(client, seeded, db):
    owner = await _setup(db, seeded, "4")
    token = await login(client, "admin.dev4")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)

    # OPEN -> triage first (close is illegal from OPEN/TRIAGE entirely -- state machine catches that).
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/close",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 1, "conclusion": "x"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_close_requires_signature_when_policy_requires_it(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.dev19")
        db.add(SignaturePolicy(record_type="deviation_record", action="disposition", meaning="Approved", signature_required=False))
        db.add(SignaturePolicy(record_type="deviation_record", action="close", meaning="Approved", signature_required=True))
    token = await login(client, "admin.dev19")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact found", "capa_required": False,
            "capa_rationale": "isolated event, no systemic pattern",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/close",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version, "conclusion": "closed, no issue found"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_disposition_blocked_without_containment(client, seeded, db):
    owner = await _setup(db, seeded, "5")
    token = await login(client, "admin.dev5")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/triage",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 1, "severity": "major", "investigation_priority": "high"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    # Skipping /contain entirely: /investigation itself is illegal from TRIAGE (state machine), so the
    # only way to reach a containment-less disposition attempt is impossible via the linear pipeline --
    # this proves the state machine itself enforces DEV-FR-005 ahead of the data-completeness check.
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/investigation",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 2, "investigator_subject_id": str(owner.id), "due_date": datetime.now(timezone.utc).isoformat()},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_contain_requires_correction_or_containment_data(client, seeded, db):
    owner = await _setup(db, seeded, "6")
    token = await login(client, "admin.dev6")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    await client.post(
        f"/qms/v1/deviations/{deviation_id}/triage",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 1, "severity": "major", "investigation_priority": "high"},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/contain",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 2},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "CONTAINMENT_REQUIRED"


async def test_root_cause_no_assignable_cause_requires_justification(client, seeded, db):
    owner = await _setup(db, seeded, "7")
    token = await login(client, "admin.dev7")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    await client.post(
        f"/qms/v1/deviations/{deviation_id}/triage",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 1, "severity": "major", "investigation_priority": "high"},
        headers=auth_headers(token),
    )
    await client.post(
        f"/qms/v1/deviations/{deviation_id}/contain",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 2, "immediate_correction": {"description": "reprocessed"}},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/investigation",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 3,
            "investigator_subject_id": str(owner.id), "due_date": datetime.now(timezone.utc).isoformat(),
            "root_cause": {"no_assignable_cause": True},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/investigation",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 3,
            "investigator_subject_id": str(owner.id), "due_date": datetime.now(timezone.utc).isoformat(),
            "root_cause": {"no_assignable_cause": True, "justification": "no plausible mechanism identified after full review"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_extend_retains_old_due_date(client, seeded, db):
    owner = await _setup(db, seeded, "8")
    token = await login(client, "admin.dev8")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)

    new_due = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/extend",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 5,
            "new_due_date": new_due, "reason": "awaiting supplier lab results", "risk_review": "no product impact from delay",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms.models import DeviationRecord
    deviation = await db.get(DeviationRecord, uuid.UUID(deviation_id))
    assert len(deviation.extension_history) == 1
    assert deviation.extension_history[0]["reason"] == "awaiting supplier lab results"
    assert deviation.due_date.isoformat().startswith(new_due[:10])


async def test_reopen_preserves_prior_closure(client, seeded, db):
    owner = await _setup(db, seeded, "9")
    token = await login(client, "admin.dev9")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact", "capa_required": False, "capa_rationale": "n/a",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/close",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version, "conclusion": "closed, no issue found"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    from app.modules.qms.models import DeviationRecord
    deviation = await db.get(DeviationRecord, uuid.UUID(deviation_id))
    first_closed_at = deviation.closed_at

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/reopen",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "reason": "new lab result received", "new_evidence": "retest shows trend toward OOS",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    await db.refresh(deviation)
    assert deviation.state == "REOPENED"
    assert deviation.closed_at == first_closed_at  # DEV-FR-020: prior closure preserved, never overwritten
    assert len(deviation.reopen_history) == 1

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/close",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version, "conclusion": "reconfirmed no impact after retest"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    await db.refresh(deviation)
    assert deviation.closed_at == first_closed_at
    assert len(deviation.closure_history) == 2


async def test_planned_deviation_requires_scope_bounds(client, seeded, db):
    owner = await _setup(db, seeded, "10")
    token = await login(client, "admin.dev10")
    resp = await client.post(
        "/qms/v1/deviations", json=_create_body(seeded["site_id"], owner.id, planned=True), headers=auth_headers(token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_planned_deviation_expired_blocks_triage(client, seeded, db):
    owner = await _setup(db, seeded, "11")
    token = await login(client, "admin.dev11")
    past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    deviation_id = await _create(
        client, token, seeded["site_id"], owner.id, planned=True,
        planned_scope={"scope": "line 2 changeover", "start_date": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(), "end_date": past},
    )
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/triage",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 1, "severity": "minor", "investigation_priority": "low"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "PLANNED_DEVIATION_EXPIRED"


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "12")
    token = await login(client, "admin.dev12")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/triage",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 99, "severity": "major", "investigation_priority": "high"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "13")
    token = await login(client, "admin.dev13")
    key = idem()
    body = _create_body(seeded["site_id"], owner.id)
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/deviations", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/deviations", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["command_id"] == resp2.json()["command_id"]
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]


async def test_duplicate_idempotency_key_different_payload_conflicts(client, seeded, db):
    owner = await _setup(db, seeded, "14")
    token = await login(client, "admin.dev14")
    key = idem()
    body1 = _create_body(seeded["site_id"], owner.id, deviation_number="DEV-IDEM-A")
    body1["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/deviations", json=body1, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    body2 = _create_body(seeded["site_id"], owner.id, deviation_number="DEV-IDEM-B")
    body2["idempotency_key"] = key
    resp2 = await client.post("/qms/v1/deviations", json=body2, headers=auth_headers(token))
    assert resp2.status_code == 409, resp2.text
    assert resp2.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_disposition_fails_closed_when_signature_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.dev15")
        # Deliberately no SignaturePolicy(record_type="deviation_record", action="disposition", ...) row.
        db.add(SignaturePolicy(record_type="deviation_record", action="close", meaning="Approved", signature_required=False))
    token = await login(client, "admin.dev15")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact", "capa_required": False, "capa_rationale": "n/a",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_disposition_invalid_code_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "16")
    token = await login(client, "admin.dev16")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "NOT_A_REAL_CODE", "disposition_rationale": "x", "capa_required": False, "capa_rationale": "n/a",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_evidence_and_impact_links_recorded(client, seeded, db):
    owner = await _setup(db, seeded, "17")
    token = await login(client, "admin.dev17")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    await client.post(
        f"/qms/v1/deviations/{deviation_id}/triage",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 1, "severity": "major", "investigation_priority": "high"},
        headers=auth_headers(token),
    )
    await client.post(
        f"/qms/v1/deviations/{deviation_id}/contain",
        json={"idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 2, "immediate_correction": {"description": "reprocessed"}},
        headers=auth_headers(token),
    )
    linked_batch = str(uuid.uuid4())
    cross_batch = str(uuid.uuid4())
    plan = {"records": ["batch record BAT-9"], "interviews": ["line operator"], "technical_evidence": ["environmental log"]}
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/investigation",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": 3,
            "investigator_subject_id": str(owner.id), "due_date": datetime.now(timezone.utc).isoformat(),
            "root_cause": {"method": "fishbone", "no_assignable_cause": False},
            "evidence_links": [{"impacted_record_type": "batch", "impacted_record_id": linked_batch}],
            "investigation_plan": plan, "cross_batch_ids": [cross_batch],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms import service as qms_service
    from app.modules.qms.models import DeviationRecord
    links = await qms_service.get_impact_links(db, uuid.UUID(deviation_id))
    assert len(links) == 1
    assert str(links[0].impacted_record_id) == linked_batch
    assert links[0].impact_category is None

    deviation = await db.get(DeviationRecord, uuid.UUID(deviation_id))
    assert deviation.investigation_plan == plan
    assert deviation.cross_batch_ids == [cross_batch]


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.dev20")
        # deliberately no SignaturePolicy row for deviation_record/disposition
    token = await login(client, "admin.dev20")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/signature-challenges",
        json={"action": "disposition"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_deviation(client, seeded, db):
    owner = await _setup(db, seeded, "21")
    token = await login(client, "admin.dev21")
    resp = await client.post(
        f"/qms/v1/deviations/{uuid.uuid4()}/signature-challenges",
        json={"action": "disposition"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_disposition(client, seeded, db):
    owner = await _setup(db, seeded, "22", signed=True)
    token = await login(client, "admin.dev22")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/signature-challenges",
        json={"action": "disposition"}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Approved"
    assert body["challenge_id"]
    assert body["expires_at"]

    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact found", "capa_required": False,
            "capa_rationale": "isolated event, no systemic pattern",
            "challenge_id": body["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


async def test_signature_challenge_unknown_action_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "23", signed=True)
    token = await login(client, "admin.dev23")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/signature-challenges",
        json={"action": "not_a_real_action"}, headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


# =================================================================================================
# SG-060 gap resolution: change_control_id / training_assignment_id FK on disposition
# =================================================================================================


async def test_disposition_links_existing_change_control_and_training_assignment(client, seeded, db):
    from app.modules.qms.change_models import ChangeControl
    from app.modules.qms.models import DeviationRecord
    from app.modules.qms.training_models import TrainingAssignment, TrainingRequirement

    owner = await _setup(db, seeded, "24")
    async with db.begin():
        cc = ChangeControl(
            site_id=seeded["site_id"], change_number=f"CHG-{uuid.uuid4().hex[:8]}", change_type="process",
            classification="permanent", current_state={"desc": "as-is"}, proposed_state={"desc": "to-be"},
            reason="deviation follow-up", owner_subject_id=owner.id, version=1,
        )
        db.add(cc)
        req = TrainingRequirement(
            site_id=seeded["site_id"], title="Retrain on revised SOP", source_type="deviation", training_type="sop",
            version=1,
        )
        db.add(req)
        await db.flush()
        ta = TrainingAssignment(
            site_id=seeded["site_id"], subject_id=owner.id, requirement_id=req.id, assigned_by_user_id=owner.id,
            version=1,
        )
        db.add(ta)
        await db.flush()
        cc_id, ta_id = cc.id, ta.id

    token = await login(client, "admin.dev24")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact found", "capa_required": False,
            "capa_rationale": "isolated event, no systemic pattern",
            "change_control_required": True, "change_control_rationale": "SOP must change",
            "change_control_id": str(cc_id),
            "training_required": True, "training_rationale": "operators must retrain",
            "training_assignment_id": str(ta_id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    deviation = await db.get(DeviationRecord, uuid.UUID(deviation_id))
    assert deviation.change_control_id == cc_id
    assert deviation.training_assignment_id == ta_id


async def test_disposition_rejects_unknown_change_control_id(client, seeded, db):
    owner = await _setup(db, seeded, "25")
    token = await login(client, "admin.dev25")
    deviation_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_disposition(client, token, deviation_id, investigator_id=owner.id)
    resp = await client.post(
        f"/qms/v1/deviations/{deviation_id}/disposition",
        json={
            "idempotency_key": idem(), "deviation_id": deviation_id, "expected_version": next_version,
            "disposition_code": "CONTINUE", "disposition_rationale": "no impact found", "capa_required": False,
            "capa_rationale": "isolated event, no systemic pattern",
            "change_control_required": True, "change_control_rationale": "SOP must change",
            "change_control_id": str(uuid.uuid4()),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["code"] == "NOT_FOUND"
