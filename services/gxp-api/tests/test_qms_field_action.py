"""Document 36 (SPEC-QMS-011) -- the buildable slice: create field action -> scope -> reportability
(signed) -> approve (signed) -> communications -> reconcile -> effectiveness -> close (signed), matching
the module's own 8-op API list and the fold-in pattern documented in
app/modules/qms/field_action_models.py's module docstring. New module. FAR-FR-008/016/020 are out of scope
this pass -- see docs/generated/18_SPEC_GAPS.md SG-105/SG-106.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.product_master.models import ProductVersion
from app.modules.qms.field_action_models import FieldAction, FieldActionCommunication, FieldActionReconciliation, FieldActionScopeItem
from app.modules.qms.risk_models import RiskRecord
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
        version_no=1, name="Test Infusion Pump", lifecycle_state="released",
        manufacturing_profile_code="standard", site_id=seeded["site_id"],
    )
    db.add(product)
    await db.flush()
    return product.id


async def _make_risk(db, seeded, owner) -> uuid.UUID:
    risk = RiskRecord(
        site_id=seeded["site_id"], risk_number=f"RSK-{uuid.uuid4().hex[:8]}", risk_type="product",
        hazard_problem="Spring tension out of spec.", potential_effect="Underdose risk.", owner_subject_id=owner.id,
    )
    db.add(risk)
    await db.flush()
    return risk.id


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


async def _setup(db, seeded, tag, *, signed=False, approve_signed=None, reportability_signed=None):
    approve_signed = signed if approve_signed is None else approve_signed
    reportability_signed = signed if reportability_signed is None else reportability_signed
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.far{tag}")
        # SG-138 (2026-09-10): Document 106 section 9 rows 103/104/105 -- approve/close `Approved` by a
        # "QA Releaser" (independent of the author/owner -- but FieldAction stores no such identity, so
        # only the role is enforced); reportability `Approved` by a "Regulatory Affairs authorized
        # submitter" -> the "Postmarket Regulatory Affairs" role, human-only.
        db.add(SignaturePolicy(
            record_type="field_action", action="close", meaning="Approved", signature_required=signed,
            required_role_id=(seeded["roles"]["QA Releaser"].id if signed else None),
            requires_independent_signer=signed,
        ))
        db.add(SignaturePolicy(
            record_type="field_action", action="approve", meaning="Approved", signature_required=approve_signed,
            required_role_id=(seeded["roles"]["QA Releaser"].id if approve_signed else None),
            requires_independent_signer=bool(approve_signed),
        ))
        db.add(SignaturePolicy(
            record_type="field_action", action="reportability", meaning="Approved",
            signature_required=reportability_signed,
            required_role_id=(seeded["roles"]["Postmarket Regulatory Affairs"].id if reportability_signed else None),
        ))
        product_id = await _make_product(db, seeded)
        risk_id = await _make_risk(db, seeded, owner)
    return owner, product_id, risk_id


def _create_body(site_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "action_number": f"FA-{uuid.uuid4().hex[:8]}",
        "action_type": "recall", "trigger_ref": {"source_type": "complaint", "source_id": str(uuid.uuid4())},
    }
    body.update(overrides)
    return body


async def _create_field_action(client, token, site_id, **overrides):
    resp = await client.post("/qms/v1/field-actions", json=_create_body(site_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _define_scope(client, token, field_action_id, expected_version, product_id, **overrides):
    body = {
        "idempotency_key": idem(), "field_action_id": field_action_id, "expected_version": expected_version,
        "items": [{"product_ref": str(product_id), "lot_batch_serial_refs": {"lot": "LOT-9001"}, "distribution_hold": True, "action_required": "return"}],
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/field-actions/{field_action_id}/scope", json=body, headers=auth_headers(token))
    return resp


async def _reportability(client, token, field_action_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "field_action_id": field_action_id, "expected_version": expected_version,
        "applicable_regimes": ["PART_806"], "rationale": "Device malfunction meets correction reporting criteria.",
        "decision": "reportable",
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/field-actions/{field_action_id}/reportability", json=body, headers=auth_headers(token))
    return resp


async def _approve(client, token, field_action_id, expected_version, **overrides):
    body = {"idempotency_key": idem(), "field_action_id": field_action_id, "expected_version": expected_version, "conclusion": "Plan and communications approved."}
    body.update(overrides)
    resp = await client.post(f"/qms/v1/field-actions/{field_action_id}/approve", json=body, headers=auth_headers(token))
    return resp


async def _communicate(client, token, field_action_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "field_action_id": field_action_id, "expected_version": expected_version,
        "recipient": "distributor@example.com", "message": "Please return affected units per instructions.",
        "channel": "email", "sent_at": datetime.now(timezone.utc).isoformat(),
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/field-actions/{field_action_id}/communications", json=body, headers=auth_headers(token))
    return resp


async def _reconcile(client, token, field_action_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "field_action_id": field_action_id, "expected_version": expected_version,
        "affected_count": 10, "contacted_count": 10, "returned_count": 10, "corrected_count": 10,
        "destroyed_count": 0, "unavailable_count": 0, "outstanding_count": 0,
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/field-actions/{field_action_id}/reconcile", json=body, headers=auth_headers(token))
    return resp


async def _effectiveness(client, token, field_action_id, expected_version, **overrides):
    body = {"idempotency_key": idem(), "field_action_id": field_action_id, "expected_version": expected_version, "result": "pass", "evidence": {"units_checked": 10}}
    body.update(overrides)
    resp = await client.post(f"/qms/v1/field-actions/{field_action_id}/effectiveness", json=body, headers=auth_headers(token))
    return resp


async def _close(client, token, field_action_id, expected_version, **overrides):
    body = {"idempotency_key": idem(), "field_action_id": field_action_id, "expected_version": expected_version, "conclusion": "All units accounted for; effectiveness confirmed."}
    body.update(overrides)
    resp = await client.post(f"/qms/v1/field-actions/{field_action_id}/close", json=body, headers=auth_headers(token))
    return resp


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/field-actions", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_rejects_unknown_action_type(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "1")
    token = await login(client, "admin.far1")
    resp = await client.post(
        "/qms/v1/field-actions", json=_create_body(seeded["site_id"], action_type="teleport"), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_scope_requires_at_least_one_item(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "2")
    token = await login(client, "admin.far2")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])

    resp = await _define_scope(client, token, field_action_id, 1, product_id, items=[])
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "FIELD_ACTION_SCOPE_REQUIRED"


async def test_full_lifecycle_success(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "3", signed=False)
    token = await login(client, "admin.far3")
    field_action_id = await _create_field_action(client, token, seeded["site_id"], risk_assessment_ref=str(risk_id))

    resp = await _define_scope(client, token, field_action_id, 1, product_id)
    assert resp.status_code == 200, resp.text  # 1 -> 2

    resp = await _reportability(
        client, token, field_action_id, 2, capa_required=True, capa_rationale="Root cause is a systemic supplier issue.",
        submission_reference="FDA-806-2026-0042", submission_status="submitted",
    )
    assert resp.status_code == 200, resp.text  # 2 -> 3

    resp = await _approve(client, token, field_action_id, 3)
    assert resp.status_code == 200, resp.text  # 3 -> 4

    resp = await _communicate(client, token, field_action_id, 4, ack_status="acknowledged")
    assert resp.status_code == 200, resp.text  # 4 -> 5

    resp = await _reconcile(client, token, field_action_id, 5)
    assert resp.status_code == 200, resp.text  # 5 -> 6

    resp = await _effectiveness(client, token, field_action_id, 6)
    assert resp.status_code == 200, resp.text  # 6 -> 7

    resp = await _close(client, token, field_action_id, 7)
    assert resp.status_code == 200, resp.text  # 7 -> 8
    assert resp.json()["resulting_version"] == 8

    field_action = await db.get(FieldAction, uuid.UUID(field_action_id))
    assert field_action.state == "CLOSED"
    assert field_action.closed_at is not None
    assert field_action.capa_required is True
    assert field_action.capa_rationale == "Root cause is a systemic supplier issue."
    assert field_action.reportability_assessment["decision"] == "reportable"
    assert field_action.reportability_assessment["submission_reference"] == "FDA-806-2026-0042"
    assert field_action.reportability_assessment["submission_status"] == "submitted"
    assert field_action.risk_assessment_ref == risk_id
    assert field_action.effectiveness_check["result"] == "pass"

    scope_item = (
        await db.execute(select(FieldActionScopeItem).where(FieldActionScopeItem.field_action_id == field_action.id))
    ).scalars().first()
    assert scope_item.distribution_hold is True
    assert scope_item.action_required == "return"

    communication = (
        await db.execute(select(FieldActionCommunication).where(FieldActionCommunication.field_action_id == field_action.id))
    ).scalar_one()
    assert communication.recipient == "distributor@example.com"
    assert communication.channel == "email"
    assert communication.ack_status == "acknowledged"

    reconciliation = (
        await db.execute(select(FieldActionReconciliation).where(FieldActionReconciliation.field_action_id == field_action.id))
    ).scalar_one()
    assert reconciliation.outstanding_count == 0
    assert reconciliation.returned_count == 10

    create_rows = (
        await db.execute(
            select(AuditEvent).where(AuditEvent.aggregate_type == "field_action", AuditEvent.aggregate_id == field_action.id, AuditEvent.action == "Created")
        )
    ).scalars().all()
    assert len(create_rows) == 1


async def test_not_reportable_decision_still_proceeds_to_closure(client, seeded, db):
    """FAR-FR-015: correction/removal records are maintained even when the reportability decision is 'no'."""
    owner, product_id, risk_id = await _setup(db, seeded, "16", signed=False)
    token = await login(client, "admin.far16")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)
    resp = await _reportability(client, token, field_action_id, 2, decision="not_reportable")
    assert resp.status_code == 200, resp.text
    await _approve(client, token, field_action_id, 3)
    await _communicate(client, token, field_action_id, 4)
    await _reconcile(client, token, field_action_id, 5)
    await _effectiveness(client, token, field_action_id, 6)
    resp = await _close(client, token, field_action_id, 7)
    assert resp.status_code == 200, resp.text

    field_action = await db.get(FieldAction, uuid.UUID(field_action_id))
    assert field_action.state == "CLOSED"
    assert field_action.reportability_assessment["decision"] == "not_reportable"


async def test_close_after_close_is_illegal_transition(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "17", signed=False)
    token = await login(client, "admin.far17")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)
    await _reportability(client, token, field_action_id, 2)
    await _approve(client, token, field_action_id, 3)
    await _communicate(client, token, field_action_id, 4)
    await _reconcile(client, token, field_action_id, 5)
    await _effectiveness(client, token, field_action_id, 6)
    resp = await _close(client, token, field_action_id, 7)
    assert resp.status_code == 200, resp.text

    resp = await _close(client, token, field_action_id, 8)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_scope_expansion_reopens_closed_field_action(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "4", signed=False)
    token = await login(client, "admin.far4")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)
    await _reportability(client, token, field_action_id, 2)
    await _approve(client, token, field_action_id, 3)
    await _communicate(client, token, field_action_id, 4)
    await _reconcile(client, token, field_action_id, 5)
    await _effectiveness(client, token, field_action_id, 6)
    resp = await _close(client, token, field_action_id, 7)
    assert resp.status_code == 200, resp.text

    field_action = await db.get(FieldAction, uuid.UUID(field_action_id))
    assert field_action.state == "CLOSED"
    assert field_action.revision == 1

    resp = await _define_scope(client, token, field_action_id, 8, product_id)
    assert resp.status_code == 200, resp.text  # scope expansion: 8 -> 9

    await db.refresh(field_action)
    assert field_action.state == "SCOPE_DEFINITION"
    assert field_action.revision == 2
    assert field_action.closed_at is None


async def test_approve_requires_reportability_first(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "5", signed=False)
    token = await login(client, "admin.far5")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)

    resp = await _approve(client, token, field_action_id, 2)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "REPORTABILITY_ASSESSMENT_REQUIRED"


async def test_communications_requires_approval_first(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "6", signed=False)
    token = await login(client, "admin.far6")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)
    await _reportability(client, token, field_action_id, 2)

    resp = await _communicate(client, token, field_action_id, 3)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "COMMUNICATION_NOT_APPROVED"


async def test_close_requires_no_outstanding_units(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "7", signed=False)
    token = await login(client, "admin.far7")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)
    await _reportability(client, token, field_action_id, 2)
    await _approve(client, token, field_action_id, 3)
    await _communicate(client, token, field_action_id, 4)
    await _reconcile(client, token, field_action_id, 5, outstanding_count=2)
    await _effectiveness(client, token, field_action_id, 6)

    resp = await _close(client, token, field_action_id, 7)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "RECONCILIATION_INCOMPLETE"


async def test_close_requires_effectiveness_first(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "8", signed=False)
    token = await login(client, "admin.far8")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)
    await _reportability(client, token, field_action_id, 2)
    await _approve(client, token, field_action_id, 3)
    await _communicate(client, token, field_action_id, 4)
    await _reconcile(client, token, field_action_id, 5)

    resp = await _close(client, token, field_action_id, 6)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "FIELD_ACTION_CLOSURE_BLOCKED"


async def test_stale_version_rejected(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "9", signed=False)
    token = await login(client, "admin.far9")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])

    resp = await _define_scope(client, token, field_action_id, 99, product_id)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_idempotent_replay_returns_same_receipt(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "10", signed=False)
    token = await login(client, "admin.far10")
    key = idem()
    body = _create_body(seeded["site_id"])
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/field-actions", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/field-actions", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]

    body2 = dict(body)
    body2["action_type"] = "removal"
    resp3 = await client.post("/qms/v1/field-actions", json=body2, headers=auth_headers(token))
    assert resp3.status_code == 409, resp3.text
    assert resp3.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_reportability_requires_signature_when_policy_requires_it(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "11", signed=False, reportability_signed=True)
    await _indep_user(db, seeded, "ra.far11", "Postmarket Regulatory Affairs")
    token = await login(client, "admin.far11")
    ra_token = await login(client, "ra.far11")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)

    resp = await _reportability(client, ra_token, field_action_id, 2)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_approve_requires_signature_when_policy_requires_it(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "12", signed=False, approve_signed=True)
    await _indep_user(db, seeded, "qa.far12", "QA Releaser")
    token = await login(client, "admin.far12")
    releaser_token = await login(client, "qa.far12")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)
    await _reportability(client, token, field_action_id, 2)

    resp = await _approve(client, releaser_token, field_action_id, 3)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_close_requires_signature_when_policy_requires_it(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "13", signed=True, approve_signed=False, reportability_signed=False)
    await _indep_user(db, seeded, "qa.far13", "QA Releaser")
    token = await login(client, "admin.far13")
    releaser_token = await login(client, "qa.far13")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    await _define_scope(client, token, field_action_id, 1, product_id)
    await _reportability(client, token, field_action_id, 2)
    await _approve(client, token, field_action_id, 3)
    await _communicate(client, token, field_action_id, 4)
    await _reconcile(client, token, field_action_id, 5)
    await _effectiveness(client, token, field_action_id, 6)

    resp = await _close(client, releaser_token, field_action_id, 7)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_actor_without_permission_is_denied(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "14", signed=False)
    token = await login(client, "operator1")  # Operator role has no field_action.* grant (seeded fixture)
    resp = await client.post(
        "/qms/v1/field-actions", json=_create_body(seeded["site_id"]), headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_missing_expected_version_rejected(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "15", signed=False)
    token = await login(client, "admin.far15")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])

    body = {
        "idempotency_key": idem(), "field_action_id": field_action_id,
        "items": [{"product_ref": str(product_id)}],
    }
    resp = await client.post(f"/qms/v1/field-actions/{field_action_id}/scope", json=body, headers=auth_headers(token))
    assert resp.status_code == 422, resp.text  # FastAPI/Pydantic request validation: expected_version required


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.far20")
    token = await login(client, "admin.far20")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    resp = await client.post(
        f"/qms/v1/field-actions/{field_action_id}/signature-challenges", json={"action": "reportability"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_field_action(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "21")
    token = await login(client, "admin.far21")
    resp = await client.post(
        f"/qms/v1/field-actions/{uuid.uuid4()}/signature-challenges", json={"action": "reportability"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_reportability(client, seeded, db):
    owner, product_id, risk_id = await _setup(db, seeded, "22", signed=True)
    await _indep_user(db, seeded, "ra.far22", "Postmarket Regulatory Affairs")
    token = await login(client, "admin.far22")
    ra_token = await login(client, "ra.far22")
    field_action_id = await _create_field_action(client, token, seeded["site_id"])
    resp = await _define_scope(client, token, field_action_id, 1, product_id)
    assert resp.status_code == 200, resp.text  # 1 -> 2

    resp = await client.post(
        f"/qms/v1/field-actions/{field_action_id}/signature-challenges", json={"action": "reportability"},
        headers=auth_headers(ra_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Approved"

    resp = await _reportability(
        client, ra_token, field_action_id, 2, challenge_id=body["challenge_id"], reauth_password=DEMO_PASSWORD,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
