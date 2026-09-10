"""Document 35 (SPEC-QMS-010) -- the buildable slice: create complaint -> triage -> investigation
decision -> (investigation -> reportability | reportability directly) -> response -> close (signed),
matching the module's own 7-op API list and the fold-in pattern documented in
app/modules/qms/complaint_models.py's module docstring. New module. CMP-FR-011/016/017/018/024 are out of
scope this pass -- see docs/generated/18_SPEC_GAPS.md SG-103; CMP-FR-022's field-level encryption is out of
scope -- see SG-104.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.product_master.models import ProductVersion
from app.modules.qms.complaint_models import ComplaintRecord, ComplaintReportabilityAssessment
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


async def _make_product(db, seeded) -> uuid.UUID:
    product = ProductVersion(
        product_business_id=f"PROD-{uuid.uuid4().hex[:8]}", product_code=f"CODE-{uuid.uuid4().hex[:8]}",
        version_no=1, name="Test Autoinjector", lifecycle_state="released",
        manufacturing_profile_code="standard", site_id=seeded["site_id"],
    )
    db.add(product)
    await db.flush()
    return product.id


async def _setup(db, seeded, tag, *, signed=False, reportability_signed=None):
    reportability_signed = signed if reportability_signed is None else reportability_signed
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.cmp{tag}")
        # SG-138 (2026-09-10): Document 106 section 9 rows 101/102 -- close `Approved` by a "QA Releaser"
        # (independent of the owner -- but ComplaintRecord stores no owner identity, so only the role is
        # enforced); reportability `Approved` by a "Regulatory Affairs authorized submitter" -> the
        # "Postmarket Regulatory Affairs" role, human-only (no person-independence rule).
        db.add(SignaturePolicy(
            record_type="complaint_record", action="close", meaning="Approved", signature_required=signed,
            required_role_id=(seeded["roles"]["QA Releaser"].id if signed else None),
            requires_independent_signer=signed,
        ))
        db.add(SignaturePolicy(
            record_type="complaint_record", action="reportability", meaning="Approved",
            signature_required=reportability_signed,
            required_role_id=(seeded["roles"]["Postmarket Regulatory Affairs"].id if reportability_signed else None),
        ))
        product_id = await _make_product(db, seeded)
    return owner, product_id


async def _indep_user(db, seeded, username, role_name):
    async with db.begin():
        user = User(
            username=username, email=f"{username}@example.com", full_name=role_name,
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


def _create_body(site_id, product_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "complaint_number": f"CMP-{uuid.uuid4().hex[:8]}",
        "received_at": datetime.now(timezone.utc).isoformat(), "source_channel": "written",
        "nature_code": "DEVICE_MALFUNCTION", "description": "Autoinjector failed to deliver full dose.",
        "product_ref": str(product_id), "constituent_classification": "combination",
    }
    body.update(overrides)
    return body


async def _create_complaint(client, token, site_id, product_id, **overrides):
    resp = await client.post("/qms/v1/complaints", json=_create_body(site_id, product_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _triage(client, token, complaint_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "complaint_id": complaint_id, "expected_version": expected_version,
        "triage": {"seriousness": "serious", "criticality": "high"},
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/complaints/{complaint_id}/triage", json=body, headers=auth_headers(token))
    return resp


async def _investigation_decision(client, token, complaint_id, expected_version, **overrides):
    body = {"idempotency_key": idem(), "complaint_id": complaint_id, "expected_version": expected_version, "investigation_required": True}
    body.update(overrides)
    resp = await client.post(f"/qms/v1/complaints/{complaint_id}/investigation-decision", json=body, headers=auth_headers(token))
    return resp


async def _investigate(client, token, complaint_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "complaint_id": complaint_id, "expected_version": expected_version,
        "findings": {"batch_ref": str(uuid.uuid4()), "qc_ref": str(uuid.uuid4())},
        "conclusion": "Root cause confirmed: spring tension out of spec.",
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/complaints/{complaint_id}/investigation", json=body, headers=auth_headers(token))
    return resp


async def _reportability(client, token, complaint_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "complaint_id": complaint_id, "expected_version": expected_version,
        "applicable_regimes": ["FDA_MDR"], "rationale": "Device malfunction meets MDR reportability criteria.",
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/complaints/{complaint_id}/reportability", json=body, headers=auth_headers(token))
    return resp


async def _respond(client, token, complaint_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "complaint_id": complaint_id, "expected_version": expected_version,
        "direction": "outbound", "communication_type": "response", "message": "Thank you; corrective action initiated.",
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/complaints/{complaint_id}/response", json=body, headers=auth_headers(token))
    return resp


async def _close(client, token, complaint_id, expected_version, **overrides):
    body = {"idempotency_key": idem(), "complaint_id": complaint_id, "expected_version": expected_version, "conclusion": "Investigation complete; response sent."}
    body.update(overrides)
    resp = await client.post(f"/qms/v1/complaints/{complaint_id}/close", json=body, headers=auth_headers(token))
    return resp


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/complaints", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_complaint_rejects_unknown_source_channel(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "1")
    token = await login(client, "admin.cmp1")
    resp = await client.post(
        "/qms/v1/complaints", json=_create_body(seeded["site_id"], product_id, source_channel="telepathic"), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_create_complaint_accepts_oral_channel(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "16")
    token = await login(client, "admin.cmp16")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id, source_channel="oral")
    complaint = await db.get(ComplaintRecord, uuid.UUID(complaint_id))
    assert complaint.source_channel == "oral"


async def test_triage_requires_resolved_product(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "2")
    token = await login(client, "admin.cmp2")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id, product_ref=None)

    resp = await _triage(client, token, complaint_id, 1)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "COMPLAINT_PRODUCT_UNRESOLVED"


async def test_full_lifecycle_via_investigation(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "3", signed=False)
    token = await login(client, "admin.cmp3")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)

    resp = await _triage(client, token, complaint_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2

    resp = await _investigation_decision(client, token, complaint_id, 2, investigation_required=True)
    assert resp.status_code == 200, resp.text  # 2 -> 3

    resp = await _investigate(client, token, complaint_id, 3)
    assert resp.status_code == 200, resp.text  # 3 -> 4

    due_date = datetime(2026, 9, 24, tzinfo=timezone.utc)
    resp = await _reportability(
        client, token, complaint_id, 4, capa_required=True, capa_rationale="Systemic spring-tension issue.",
        field_action_required=True, field_action_rationale="Multiple units from same lot affected.",
        due_date=due_date.isoformat(),
    )
    assert resp.status_code == 200, resp.text  # 4 -> 5
    complaint = await db.get(ComplaintRecord, uuid.UUID(complaint_id))
    assert complaint.state == "RESPONSE"

    resp = await _respond(client, token, complaint_id, 5)
    assert resp.status_code == 200, resp.text  # 5 -> 6

    resp = await _close(client, token, complaint_id, 6)
    assert resp.status_code == 200, resp.text  # 6 -> 7
    assert resp.json()["resulting_version"] == 7

    await db.refresh(complaint)
    assert complaint.state == "CLOSED"
    assert complaint.closed_at is not None

    assessment = (
        await db.execute(select(ComplaintReportabilityAssessment).where(ComplaintReportabilityAssessment.complaint_id == complaint.id))
    ).scalar_one()
    assert assessment.capa_required is True
    assert assessment.capa_rationale == "Systemic spring-tension issue."
    assert assessment.field_action_required is True
    assert assessment.field_action_rationale == "Multiple units from same lot affected."
    assert assessment.due_date is not None
    assert assessment.applicable_regimes == ["FDA_MDR"]

    create_rows = (
        await db.execute(
            select(AuditEvent).where(AuditEvent.aggregate_type == "complaint_record", AuditEvent.aggregate_id == complaint.id, AuditEvent.action == "Created")
        )
    ).scalars().all()
    assert len(create_rows) == 1


async def test_full_lifecycle_no_investigation(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "4", signed=False)
    token = await login(client, "admin.cmp4")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    await _triage(client, token, complaint_id, 1)

    resp = await _investigation_decision(client, token, complaint_id, 2, investigation_required=False, no_investigation_reason="Isolated user-error report; no product defect indicated.")
    assert resp.status_code == 200, resp.text  # 2 -> 3

    complaint = await db.get(ComplaintRecord, uuid.UUID(complaint_id))
    assert complaint.state == "NO_INVESTIGATION_JUSTIFIED"

    resp = await _reportability(client, token, complaint_id, 3)
    assert resp.status_code == 200, resp.text  # reportability reachable directly from NO_INVESTIGATION_JUSTIFIED


async def test_no_investigation_requires_rationale(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "5", signed=False)
    token = await login(client, "admin.cmp5")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    await _triage(client, token, complaint_id, 1)

    resp = await _investigation_decision(client, token, complaint_id, 2, investigation_required=False, no_investigation_reason="  ")
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "NO_INVESTIGATION_RATIONALE_REQUIRED"


async def test_reportability_requires_investigation_decision_first(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "6", signed=False)
    token = await login(client, "admin.cmp6")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    await _triage(client, token, complaint_id, 1)

    resp = await _reportability(client, token, complaint_id, 2)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVESTIGATION_DECISION_REQUIRED"


async def test_close_requires_reportability_first(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "7", signed=False)
    token = await login(client, "admin.cmp7")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    await _triage(client, token, complaint_id, 1)
    await _investigation_decision(client, token, complaint_id, 2, investigation_required=True)

    resp = await _close(client, token, complaint_id, 3)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "REPORTABILITY_ASSESSMENT_REQUIRED"


async def test_close_requires_a_recorded_response(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "8", signed=False)
    token = await login(client, "admin.cmp8")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    await _triage(client, token, complaint_id, 1)
    await _investigation_decision(client, token, complaint_id, 2, investigation_required=False, no_investigation_reason="No defect confirmed.")
    await _reportability(client, token, complaint_id, 3)

    resp = await _close(client, token, complaint_id, 4)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "COMPLAINT_CLOSURE_BLOCKED"


async def test_duplicate_detected_without_deleting_original(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "9", signed=False)
    token = await login(client, "admin.cmp9")

    first_id = await _create_complaint(client, token, seeded["site_id"], product_id, nature_code="LEAK")
    second_id = await _create_complaint(client, token, seeded["site_id"], product_id, nature_code="LEAK")

    first = await db.get(ComplaintRecord, uuid.UUID(first_id))
    second = await db.get(ComplaintRecord, uuid.UUID(second_id))
    assert first.is_potential_duplicate is False
    assert second.is_potential_duplicate is True
    assert second.related_complaint_ids == [first_id]
    # Original intake is untouched -- still readable, not deleted.
    assert first.nature_code == "LEAK"


async def test_stale_version_rejected(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "10", signed=False)
    token = await login(client, "admin.cmp10")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)

    resp = await _triage(client, token, complaint_id, 99)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_idempotent_replay_returns_same_receipt(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "11", signed=False)
    token = await login(client, "admin.cmp11")
    key = idem()
    body = _create_body(seeded["site_id"], product_id)
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/complaints", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/complaints", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]

    body2 = dict(body)
    body2["nature_code"] = "DIFFERENT_CODE"
    resp3 = await client.post("/qms/v1/complaints", json=body2, headers=auth_headers(token))
    assert resp3.status_code == 409, resp3.text
    assert resp3.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_reportability_requires_signature_when_policy_requires_it(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "12", signed=False, reportability_signed=True)
    await _indep_user(db, seeded, "ra.cmp12", "Postmarket Regulatory Affairs")
    token = await login(client, "admin.cmp12")
    ra_token = await login(client, "ra.cmp12")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    await _triage(client, token, complaint_id, 1)
    await _investigation_decision(client, token, complaint_id, 2, investigation_required=False, no_investigation_reason="No defect confirmed.")

    resp = await _reportability(client, ra_token, complaint_id, 3)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_close_requires_signature_when_policy_requires_it(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "13", signed=True, reportability_signed=False)
    await _indep_user(db, seeded, "qa.cmp13", "QA Releaser")
    token = await login(client, "admin.cmp13")
    releaser_token = await login(client, "qa.cmp13")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    await _triage(client, token, complaint_id, 1)
    await _investigation_decision(client, token, complaint_id, 2, investigation_required=False, no_investigation_reason="No defect confirmed.")
    await _reportability(client, token, complaint_id, 3)
    await _respond(client, token, complaint_id, 4)

    resp = await _close(client, releaser_token, complaint_id, 5)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_actor_without_permission_is_denied(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "14", signed=False)
    token = await login(client, "operator1")  # Operator role has no complaint.* grant (seeded fixture)
    resp = await client.post(
        "/qms/v1/complaints", json=_create_body(seeded["site_id"], product_id), headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_missing_expected_version_rejected(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "15", signed=False)
    token = await login(client, "admin.cmp15")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)

    body = {"idempotency_key": idem(), "complaint_id": complaint_id, "triage": {"seriousness": "minor"}}
    resp = await client.post(f"/qms/v1/complaints/{complaint_id}/triage", json=body, headers=auth_headers(token))
    assert resp.status_code == 422, resp.text  # FastAPI/Pydantic request validation: expected_version required


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.cmp20")
        product_id = await _make_product(db, seeded)
    token = await login(client, "admin.cmp20")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    resp = await client.post(
        f"/qms/v1/complaints/{complaint_id}/signature-challenges", json={"action": "reportability"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_complaint(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "21")
    token = await login(client, "admin.cmp21")
    resp = await client.post(
        f"/qms/v1/complaints/{uuid.uuid4()}/signature-challenges", json={"action": "reportability"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_reportability(client, seeded, db):
    owner, product_id = await _setup(db, seeded, "22", signed=True)
    await _indep_user(db, seeded, "ra.cmp22", "Postmarket Regulatory Affairs")
    token = await login(client, "admin.cmp22")
    ra_token = await login(client, "ra.cmp22")
    complaint_id = await _create_complaint(client, token, seeded["site_id"], product_id)
    await _triage(client, token, complaint_id, 1)
    await _investigation_decision(
        client, token, complaint_id, 2, investigation_required=False, no_investigation_reason="Isolated user-error report.",
    )

    resp = await client.post(
        f"/qms/v1/complaints/{complaint_id}/signature-challenges", json={"action": "reportability"},
        headers=auth_headers(ra_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Approved"

    resp = await _reportability(
        client, ra_token, complaint_id, 3, challenge_id=body["challenge_id"], reauth_password=DEMO_PASSWORD,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
