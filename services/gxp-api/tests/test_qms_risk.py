"""Document 33 (SPEC-QMS-008) -- the buildable slice: create risk -> initial assessment -> controls ->
residual assessment -> accept -> review (still_current / reassessment_required -> new cycle), matching the
module's own 6-op API list and the fold-in pattern documented in app/modules/qms/risk_models.py's module
docstring. New module. RSK-FR-007's risk-tiered authority escalation and RSK-FR-009/010/014's cross-module
auto-trigger wiring are out of scope this pass -- see docs/generated/18_SPEC_GAPS.md SG-099/SG-100.
"""

import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.qms.risk_models import RiskAssessmentVersion, RiskRecord
from app.modules.rules.models import RuleDefinition
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


async def _make_released_methodology(db, tag: str) -> uuid.UUID:
    rule = RuleDefinition(
        rule_id=f"risk-methodology-{tag}", rule_type="risk_methodology", semantic_version="1.0.0",
        status="released", expression_ast={}, input_contract={}, output_contract={},
        unit_policy={}, precision_policy={}, rounding_policy={},
    )
    db.add(rule)
    await db.flush()
    return rule.rule_object_id


async def _setup(db, seeded, tag, *, signed=False):
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.risk{tag}")
        # SG-138 (2026-09-10): Document 106 section 9 row 97 -- review `Reviewed` by a "QA Reviewer"
        # independent of the performer (checked against the risk record's `owner_subject_id`).
        db.add(SignaturePolicy(
            record_type="risk_record", action="review", meaning="Reviewed", signature_required=signed,
            required_role_id=(seeded["roles"]["QA Reviewer"].id if signed else None),
            requires_independent_signer=signed,
        ))
        methodology_id = await _make_released_methodology(db, tag)
    return owner, methodology_id


async def _indep_qa_reviewer(db, seeded, username):
    async with db.begin():
        user = User(
            username=username, email=f"{username}@example.com", full_name="Indep QA Reviewer",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Reviewer"].id))
    return user


def _create_body(site_id, owner_id, methodology_id=None, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "risk_number": f"RSK-{uuid.uuid4().hex[:8]}",
        "risk_type": "process", "hazard_problem": "Powder segregation during blending.",
        "potential_effect": "Content uniformity failure in finished product.",
        "owner_subject_id": str(owner_id),
    }
    if methodology_id is not None:
        body["methodology_id"] = str(methodology_id)
    body.update(overrides)
    return body


async def _create_risk(client, token, site_id, owner_id, methodology_id=None, **overrides):
    resp = await client.post("/qms/v1/risks", json=_create_body(site_id, owner_id, methodology_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _add_initial_assessment(client, token, risk_id, expected_version, methodology_id=None, **overrides):
    body = {
        "idempotency_key": idem(), "risk_id": risk_id, "expected_version": expected_version,
        "scoring_inputs": {"severity": 4, "occurrence": 3, "detection": 2},
        "score": {"rpn": 24, "class": "medium"},
    }
    if methodology_id is not None:
        body["methodology_id"] = str(methodology_id)
    body.update(overrides)
    resp = await client.post(f"/qms/v1/risks/{risk_id}/assessments", json=body, headers=auth_headers(token))
    return resp


async def _add_controls(client, token, risk_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "risk_id": risk_id, "expected_version": expected_version,
        "controls": [{"type": "preventive", "description": "Add anti-segregation baffle.", "evidence": "ECO-4471"}],
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/risks/{risk_id}/controls", json=body, headers=auth_headers(token))
    return resp


async def _add_residual_assessment(client, token, risk_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "risk_id": risk_id, "expected_version": expected_version,
        "scoring_inputs": {"severity": 4, "occurrence": 1, "detection": 2},
        "score": {"rpn": 8, "class": "low"},
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/risks/{risk_id}/assessments", json=body, headers=auth_headers(token))
    return resp


async def _accept(client, token, risk_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "risk_id": risk_id, "expected_version": expected_version,
        "accepted_role": "QA Manager", "rationale": "Residual risk is acceptable after mitigation.",
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/risks/{risk_id}/accept", json=body, headers=auth_headers(token))
    return resp


async def _review(client, token, risk_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "risk_id": risk_id, "expected_version": expected_version,
        "trigger_type": "periodic", "outcome": "still_current", "rationale": "No new signals since acceptance.",
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/risks/{risk_id}/review", json=body, headers=auth_headers(token))
    return resp


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/risks", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_risk_requires_hazard_and_effect(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "1")
    token = await login(client, "admin.risk1")
    resp = await client.post(
        "/qms/v1/risks", json=_create_body(seeded["site_id"], owner.id, hazard_problem="  "), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "RISK_INPUT_INCOMPLETE"


async def test_create_risk_rejects_unknown_risk_type(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "2")
    token = await login(client, "admin.risk2")
    resp = await client.post(
        "/qms/v1/risks", json=_create_body(seeded["site_id"], owner.id, risk_type="unobtainium"), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_full_lifecycle_success(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "3", signed=False)
    token = await login(client, "admin.risk3")
    context = {"product_id": str(uuid.uuid4()), "recipe_step": "blending"}
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id, context=context)

    resp = await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)
    assert resp.status_code == 200, resp.text  # 1 -> 2

    resp = await _add_controls(
        client, token, risk_id, 2,
        mitigation_actions=[{"type": "CAPA", "reference": "CAPA-2201"}],
    )
    assert resp.status_code == 200, resp.text  # 2 -> 3

    resp = await _add_residual_assessment(client, token, risk_id, 3)
    assert resp.status_code == 200, resp.text  # 3 -> 4

    resp = await _accept(client, token, risk_id, 4)
    assert resp.status_code == 200, resp.text  # 4 -> 5

    resp = await _review(client, token, risk_id, 5, outcome="still_current")
    assert resp.status_code == 200, resp.text  # 5 -> 6
    assert resp.json()["resulting_version"] == 6

    risk = await db.get(RiskRecord, uuid.UUID(risk_id))
    assert risk.state == "ACCEPTED"
    assert risk.context == context

    version = (
        await db.execute(
            select(RiskAssessmentVersion).where(
                RiskAssessmentVersion.risk_record_id == risk.id, RiskAssessmentVersion.is_current.is_(True)
            )
        )
    ).scalar_one()
    assert version.mitigation_actions == [{"type": "CAPA", "reference": "CAPA-2201"}]

    # TC-033-M11: every committed mutation writes exactly one audit event in its own transaction.
    create_audit_rows = (
        await db.execute(
            select(AuditEvent).where(AuditEvent.aggregate_type == "risk_record", AuditEvent.aggregate_id == risk.id, AuditEvent.action == "Created")
        )
    ).scalars().all()
    assert len(create_audit_rows) == 1


async def test_review_reassessment_opens_new_cycle(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "4", signed=False)
    token = await login(client, "admin.risk4")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)
    await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)
    await _add_controls(client, token, risk_id, 2)
    await _add_residual_assessment(client, token, risk_id, 3)
    await _accept(client, token, risk_id, 4)

    resp = await _review(client, token, risk_id, 5, outcome="reassessment_required", trigger_type="triggered")
    assert resp.status_code == 200, resp.text  # 5 -> 6

    risk = await db.get(RiskRecord, uuid.UUID(risk_id))
    assert risk.state == "NEW_VERSION"

    resp = await _add_initial_assessment(client, token, risk_id, 6)
    assert resp.status_code == 200, resp.text  # 6 -> 7, cycle 2, no methodology_id needed (already bound)

    versions = (
        await db.execute(
            RiskAssessmentVersion.__table__.select().where(RiskAssessmentVersion.risk_record_id == uuid.UUID(risk_id))
        )
    ).fetchall()
    assert len(versions) == 2
    cycles = sorted(v.cycle_number for v in versions)
    assert cycles == [1, 2]
    current = [v for v in versions if v.is_current]
    assert len(current) == 1
    assert current[0].cycle_number == 2


async def test_accept_requires_residual_assessment(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "5", signed=False)
    token = await login(client, "admin.risk5")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)
    await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)
    await _add_controls(client, token, risk_id, 2)

    resp = await client.post(
        f"/qms/v1/risks/{risk_id}/accept",
        json={
            "idempotency_key": idem(), "risk_id": risk_id, "expected_version": 3,
            "accepted_role": "QA Manager", "rationale": "premature",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_add_controls_requires_at_least_one(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "6", signed=False)
    token = await login(client, "admin.risk6")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)
    await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)

    resp = await _add_controls(client, token, risk_id, 2, controls=[])
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "RISK_INPUT_INCOMPLETE"


async def test_assessment_requires_released_methodology(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "7", signed=False)
    token = await login(client, "admin.risk7")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)

    unreleased = RuleDefinition(
        rule_id="risk-methodology-draft-7", rule_type="risk_methodology", semantic_version="1.0.0",
        status="draft", expression_ast={}, input_contract={}, output_contract={},
        unit_policy={}, precision_policy={}, rounding_policy={},
    )
    db.add(unreleased)
    await db.flush()

    resp = await _add_initial_assessment(client, token, risk_id, 1, methodology_id=unreleased.rule_object_id)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "RISK_METHOD_NOT_RELEASED"


async def test_stale_version_rejected(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "8", signed=False)
    token = await login(client, "admin.risk8")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)

    resp = await _add_initial_assessment(client, token, risk_id, 99, methodology_id=methodology_id)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_idempotent_replay_returns_same_receipt(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "9", signed=False)
    token = await login(client, "admin.risk9")
    key = idem()
    body = _create_body(seeded["site_id"], owner.id, methodology_id)
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/risks", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/risks", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]

    body2 = dict(body)
    body2["risk_type"] = "product"
    resp3 = await client.post("/qms/v1/risks", json=body2, headers=auth_headers(token))
    assert resp3.status_code == 409, resp3.text
    assert resp3.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_review_requires_signature_when_policy_requires_it(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "10", signed=True)
    await _indep_qa_reviewer(db, seeded, "qa.risk10")
    token = await login(client, "admin.risk10")
    reviewer_token = await login(client, "qa.risk10")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)
    await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)
    await _add_controls(client, token, risk_id, 2)
    await _add_residual_assessment(client, token, risk_id, 3)
    await _accept(client, token, risk_id, 4)

    # Independent QA Reviewer, correct role, no challenge -> still MISSING_SIGNATURE.
    resp = await _review(client, reviewer_token, risk_id, 5)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_accept_requires_rationale(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "11", signed=False)
    token = await login(client, "admin.risk11")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)
    await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)
    await _add_controls(client, token, risk_id, 2)
    await _add_residual_assessment(client, token, risk_id, 3)

    resp = await _accept(client, token, risk_id, 4, rationale="  ")
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "RISK_ACCEPTANCE_NOT_AUTHORIZED"


async def test_actor_without_permission_is_denied(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "13", signed=False)
    token = await login(client, "operator1")  # Operator role has no risk.* grant (seeded fixture)
    resp = await client.post(
        "/qms/v1/risks", json=_create_body(seeded["site_id"], owner.id, methodology_id), headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_missing_expected_version_rejected(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "14", signed=False)
    token = await login(client, "admin.risk14")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)

    body = {
        "idempotency_key": idem(), "risk_id": risk_id,
        "scoring_inputs": {"severity": 4, "occurrence": 3, "detection": 2},
        "score": {"rpn": 24, "class": "medium"}, "methodology_id": str(methodology_id),
    }
    resp = await client.post(f"/qms/v1/risks/{risk_id}/assessments", json=body, headers=auth_headers(token))
    assert resp.status_code == 422, resp.text  # FastAPI/Pydantic request validation: expected_version required


async def test_dashboard_reports_state_and_type_counts(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "12", signed=False)
    token = await login(client, "admin.risk12")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)

    resp = await client.get(f"/qms/v1/risks/dashboard?site_id={seeded['site_id']}", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["by_state"].get("DRAFT", 0) >= 1
    assert any(r["id"] == risk_id for r in payload["risks"])


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.risk20")
    token = await login(client, "admin.risk20")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/risks/{risk_id}/signature-challenges", json={"action": "review"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_risk(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "21")
    token = await login(client, "admin.risk21")
    resp = await client.post(
        f"/qms/v1/risks/{uuid.uuid4()}/signature-challenges", json={"action": "review"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_review(client, seeded, db):
    owner, methodology_id = await _setup(db, seeded, "22", signed=True)
    await _indep_qa_reviewer(db, seeded, "qa.risk22")
    token = await login(client, "admin.risk22")
    reviewer_token = await login(client, "qa.risk22")
    risk_id = await _create_risk(client, token, seeded["site_id"], owner.id)
    assert (await _add_initial_assessment(client, token, risk_id, 1, methodology_id=methodology_id)).status_code == 200
    assert (await _add_controls(client, token, risk_id, 2)).status_code == 200
    assert (await _add_residual_assessment(client, token, risk_id, 3)).status_code == 200
    assert (await _accept(client, token, risk_id, 4)).status_code == 200

    resp = await client.post(
        f"/qms/v1/risks/{risk_id}/signature-challenges", json={"action": "review"}, headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Reviewed"

    resp = await _review(
        client, reviewer_token, risk_id, 5, outcome="still_current",
        challenge_id=body["challenge_id"], reauth_password=DEMO_PASSWORD,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
