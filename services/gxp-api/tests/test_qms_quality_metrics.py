"""Document 37 (SPEC-QMS-012) -- the buildable slice: create metric definition -> release (signed) ->
calculate snapshot -> management review package (signed); plus effectiveness checks: create -> evaluate.
Matches the module's own 7-op API list (across two prefixes) and the fold-in pattern documented in
app/modules/qms/quality_metrics_models.py's module docstring. New module. MET-FR-003..011/015/017 are out
of scope this pass -- see docs/generated/18_SPEC_GAPS.md SG-107/SG-108.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.qms.quality_metrics_models import EffectivenessCheck, QualityMetricDefinition, QualityMetricSnapshot
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


async def _setup(db, seeded, tag, *, signed=False, release_signed=None, review_signed=None):
    release_signed = signed if release_signed is None else release_signed
    review_signed = signed if review_signed is None else review_signed
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.met{tag}")
        # SG-138 (2026-09-10): Document 106 section 9 rows 106/107 -- definition/release `Released` by a
        # "QA Releaser" independent of the definition owner; snapshot/management_review `Reviewed` by a
        # "QA Reviewer" (the snapshot has no owner identity, so role-only).
        db.add(SignaturePolicy(
            record_type="quality_metric_definition", action="release", meaning="Released",
            signature_required=release_signed,
            required_role_id=(seeded["roles"]["QA Releaser"].id if release_signed else None),
            requires_independent_signer=bool(release_signed),
        ))
        db.add(SignaturePolicy(
            record_type="quality_metric_snapshot", action="management_review", meaning="Reviewed",
            signature_required=review_signed,
            required_role_id=(seeded["roles"]["QA Reviewer"].id if review_signed else None),
            requires_independent_signer=bool(review_signed),
        ))
    return owner


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


def _create_body(site_id, owner_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "metric_code": f"MET-{uuid.uuid4().hex[:8]}",
        "owner_subject_id": str(owner_id), "source_model_id": "deviation_record",
        "numerator_definition": {"count_of": "deviation_record.state=CLOSED"}, "frequency": "monthly",
    }
    body.update(overrides)
    return body


async def _create_definition(client, token, site_id, owner_id, **overrides):
    resp = await client.post("/quality-metrics/v1/definitions", json=_create_body(site_id, owner_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _release(client, token, definition_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "definition_id": definition_id, "expected_version": expected_version,
        "effective_from": datetime.now(timezone.utc).isoformat(),
    }
    body.update(overrides)
    resp = await client.post(f"/quality-metrics/v1/definitions/{definition_id}/release", json=body, headers=auth_headers(token))
    return resp


async def _calculate(client, token, site_id, definition_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "metric_definition_id": definition_id,
        "period_start": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "period_end": datetime.now(timezone.utc).isoformat(), "result": {"rate": 0.05, "count": 12},
    }
    body.update(overrides)
    resp = await client.post("/quality-metrics/v1/calculate", json=body, headers=auth_headers(token))
    return resp


async def _freeze_package(client, token, site_id, snapshot_ids, **overrides):
    body = {"idempotency_key": idem(), "site_id": str(site_id), "snapshot_ids": snapshot_ids}
    body.update(overrides)
    resp = await client.post("/quality-metrics/v1/management-review-packages", json=body, headers=auth_headers(token))
    return resp


async def _create_check(client, token, site_id, source_record_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "source_module": "capa", "source_record_id": str(source_record_id),
        "criterion": "Deviation recurrence rate drops below 5% for two consecutive quarters.",
        "observation_period_start": datetime.now(timezone.utc).isoformat(),
        "observation_period_end": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
    }
    body.update(overrides)
    resp = await client.post("/effectiveness/v1/checks", json=body, headers=auth_headers(token))
    return resp


async def _evaluate_check(client, token, check_id, expected_version, **overrides):
    body = {"idempotency_key": idem(), "check_id": check_id, "expected_version": expected_version, "result": "pass"}
    body.update(overrides)
    resp = await client.post(f"/effectiveness/v1/checks/{check_id}/evaluate", json=body, headers=auth_headers(token))
    return resp


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/quality-metrics/v1/definitions", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_definition_requires_core_fields(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.met1")
    resp = await client.post(
        "/quality-metrics/v1/definitions", json=_create_body(seeded["site_id"], owner.id, metric_code="  "), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_calculate_requires_released_definition(client, seeded, db):
    owner = await _setup(db, seeded, "2")
    token = await login(client, "admin.met2")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)

    resp = await _calculate(client, token, seeded["site_id"], definition_id)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "METRIC_DEFINITION_NOT_RELEASED"


async def test_calculate_requires_nonempty_result(client, seeded, db):
    owner = await _setup(db, seeded, "3", signed=False)
    token = await login(client, "admin.met3")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)
    await _release(client, token, definition_id, 1)

    resp = await _calculate(client, token, seeded["site_id"], definition_id, result={})
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "METRIC_SOURCE_INCOMPLETE"


async def test_full_lifecycle_success(client, seeded, db):
    owner = await _setup(db, seeded, "4", signed=False)
    token = await login(client, "admin.met4")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)

    resp = await _release(client, token, definition_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2

    resp = await _calculate(client, token, seeded["site_id"], definition_id, threshold_exceeded=True)
    assert resp.status_code == 200, resp.text
    snapshot_id = resp.json()["aggregate_id"]

    definition = await db.get(QualityMetricDefinition, uuid.UUID(definition_id))
    assert definition.state == "RELEASED"

    snapshot = await db.get(QualityMetricSnapshot, uuid.UUID(snapshot_id))
    assert snapshot.state == "COMPLETE"
    assert snapshot.result == {"rate": 0.05, "count": 12}
    assert snapshot.formula_version == "1"
    assert snapshot.threshold_exceeded is True

    resp = await _freeze_package(client, token, seeded["site_id"], [snapshot_id])
    assert resp.status_code == 200, resp.text

    await db.refresh(snapshot)
    assert snapshot.state == "FROZEN"
    assert snapshot.review_package_id is not None

    create_rows = (
        await db.execute(
            select(AuditEvent).where(AuditEvent.aggregate_type == "quality_metric_definition", AuditEvent.aggregate_id == definition.id, AuditEvent.action == "Created")
        )
    ).scalars().all()
    assert len(create_rows) == 1


async def test_release_supersedes_prior_version(client, seeded, db):
    owner = await _setup(db, seeded, "5", signed=False)
    token = await login(client, "admin.met5")
    metric_code = f"MET-{uuid.uuid4().hex[:8]}"
    first_id = await _create_definition(client, token, seeded["site_id"], owner.id, metric_code=metric_code)
    resp = await _release(client, token, first_id, 1)
    assert resp.status_code == 200, resp.text

    second_id = await _create_definition(client, token, seeded["site_id"], owner.id, metric_code=metric_code)
    second = await db.get(QualityMetricDefinition, uuid.UUID(second_id))
    assert second.version_no == 2

    resp = await _release(client, token, second_id, 1)
    assert resp.status_code == 200, resp.text

    first = await db.get(QualityMetricDefinition, uuid.UUID(first_id))
    await db.refresh(first)
    assert first.state == "SUPERSEDED"
    await db.refresh(second)
    assert second.state == "RELEASED"


async def test_freeze_rejects_already_frozen_snapshot(client, seeded, db):
    owner = await _setup(db, seeded, "6", signed=False)
    token = await login(client, "admin.met6")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)
    await _release(client, token, definition_id, 1)
    resp = await _calculate(client, token, seeded["site_id"], definition_id)
    snapshot_id = resp.json()["aggregate_id"]
    resp = await _freeze_package(client, token, seeded["site_id"], [snapshot_id])
    assert resp.status_code == 200, resp.text

    resp = await _freeze_package(client, token, seeded["site_id"], [snapshot_id])
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "MANAGEMENT_PACKAGE_FROZEN"


async def test_freeze_rejects_stale_snapshot_from_superseded_definition(client, seeded, db):
    owner = await _setup(db, seeded, "7", signed=False)
    token = await login(client, "admin.met7")
    metric_code = f"MET-{uuid.uuid4().hex[:8]}"
    first_id = await _create_definition(client, token, seeded["site_id"], owner.id, metric_code=metric_code)
    await _release(client, token, first_id, 1)
    resp = await _calculate(client, token, seeded["site_id"], first_id)
    snapshot_id = resp.json()["aggregate_id"]

    second_id = await _create_definition(client, token, seeded["site_id"], owner.id, metric_code=metric_code)
    resp = await _release(client, token, second_id, 1)
    assert resp.status_code == 200, resp.text  # supersedes first_id

    resp = await _freeze_package(client, token, seeded["site_id"], [snapshot_id])
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SNAPSHOT_STALE"


async def test_effectiveness_check_lifecycle(client, seeded, db):
    owner = await _setup(db, seeded, "8", signed=False)
    token = await login(client, "admin.met8")
    resp = await _create_check(client, token, seeded["site_id"], owner.id)
    assert resp.status_code == 200, resp.text
    check_id = resp.json()["aggregate_id"]

    check = await db.get(EffectivenessCheck, uuid.UUID(check_id))
    assert check.state == "OBSERVATION"

    resp = await _evaluate_check(client, token, check_id, 1, result="pass", evidence={"trend_reviewed": True})
    assert resp.status_code == 200, resp.text

    await db.refresh(check)
    assert check.state == "PASS"
    assert check.evidence == {"trend_reviewed": True}
    assert check.reviewer_subject_id is not None


async def test_effectiveness_check_requires_criterion(client, seeded, db):
    owner = await _setup(db, seeded, "9", signed=False)
    token = await login(client, "admin.met9")
    resp = await _create_check(client, token, seeded["site_id"], owner.id, criterion="  ")
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "EFFECTIVENESS_CRITERION_REQUIRED"


async def test_inconclusive_result_requires_next_observation_due(client, seeded, db):
    owner = await _setup(db, seeded, "10", signed=False)
    token = await login(client, "admin.met10")
    resp = await _create_check(client, token, seeded["site_id"], owner.id)
    check_id = resp.json()["aggregate_id"]

    resp = await _evaluate_check(client, token, check_id, 1, result="inconclusive")
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "EFFECTIVENESS_INCONCLUSIVE"

    resp = await _evaluate_check(
        client, token, check_id, 1, result="inconclusive",
        next_observation_due=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
    )
    assert resp.status_code == 200, resp.text
    check = await db.get(EffectivenessCheck, uuid.UUID(check_id))
    assert check.state == "INCONCLUSIVE"


async def test_failed_effectiveness_captures_escalation(client, seeded, db):
    owner = await _setup(db, seeded, "11", signed=False)
    token = await login(client, "admin.met11")
    resp = await _create_check(client, token, seeded["site_id"], owner.id)
    check_id = resp.json()["aggregate_id"]

    resp = await _evaluate_check(
        client, token, check_id, 1, result="fail", escalation_required=True, escalation_rationale="Root cause action was insufficient; CAPA reopened.",
    )
    assert resp.status_code == 200, resp.text
    check = await db.get(EffectivenessCheck, uuid.UUID(check_id))
    assert check.state == "FAIL"
    assert check.escalation_required is True
    assert check.escalation_rationale == "Root cause action was insufficient; CAPA reopened."


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "12", signed=False)
    token = await login(client, "admin.met12")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)

    resp = await _release(client, token, definition_id, 99)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_idempotent_replay_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "13", signed=False)
    token = await login(client, "admin.met13")
    key = idem()
    body = _create_body(seeded["site_id"], owner.id)
    body["idempotency_key"] = key
    resp1 = await client.post("/quality-metrics/v1/definitions", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/quality-metrics/v1/definitions", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]

    body2 = dict(body)
    body2["frequency"] = "weekly"
    resp3 = await client.post("/quality-metrics/v1/definitions", json=body2, headers=auth_headers(token))
    assert resp3.status_code == 409, resp3.text
    assert resp3.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_release_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "14", signed=False, release_signed=True)
    await _indep_user(db, seeded, "qa.met14", "QA Releaser")
    token = await login(client, "admin.met14")
    releaser_token = await login(client, "qa.met14")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)

    resp = await _release(client, releaser_token, definition_id, 1)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_management_review_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "15", signed=False, review_signed=True)
    await _indep_user(db, seeded, "qa.met15", "QA Reviewer")
    token = await login(client, "admin.met15")
    reviewer_token = await login(client, "qa.met15")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)
    await _release(client, token, definition_id, 1)
    resp = await _calculate(client, token, seeded["site_id"], definition_id)
    snapshot_id = resp.json()["aggregate_id"]

    resp = await _freeze_package(client, reviewer_token, seeded["site_id"], [snapshot_id])
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_actor_without_permission_is_denied(client, seeded, db):
    owner = await _setup(db, seeded, "16", signed=False)
    token = await login(client, "operator1")  # Operator role has no quality_metric.* grant (seeded fixture)
    resp = await client.post(
        "/quality-metrics/v1/definitions", json=_create_body(seeded["site_id"], owner.id), headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_missing_expected_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "17", signed=False)
    token = await login(client, "admin.met17")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)

    body = {"idempotency_key": idem(), "definition_id": definition_id, "effective_from": datetime.now(timezone.utc).isoformat()}
    resp = await client.post(f"/quality-metrics/v1/definitions/{definition_id}/release", json=body, headers=auth_headers(token))
    assert resp.status_code == 422, resp.text  # FastAPI/Pydantic request validation: expected_version required


async def test_dashboard_reports_latest_snapshot(client, seeded, db):
    owner = await _setup(db, seeded, "18", signed=False)
    token = await login(client, "admin.met18")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)
    await _release(client, token, definition_id, 1)
    await _calculate(client, token, seeded["site_id"], definition_id, threshold_exceeded=True)

    resp = await client.get(f"/quality-metrics/v1/dashboard?site_id={seeded['site_id']}", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    matching = [m for m in payload["metrics"] if m["latest_result"] == {"rate": 0.05, "count": 12}]
    assert matching
    assert matching[0]["threshold_exceeded"] is True


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_definition_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.met20")
    token = await login(client, "admin.met20")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/quality-metrics/v1/definitions/{definition_id}/signature-challenges", json={"action": "release"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_definition_signature_challenge_404_for_missing_definition(client, seeded, db):
    owner = await _setup(db, seeded, "21")
    token = await login(client, "admin.met21")
    resp = await client.post(
        f"/quality-metrics/v1/definitions/{uuid.uuid4()}/signature-challenges", json={"action": "release"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_definition_signature_challenge_round_trip_signs_release(client, seeded, db):
    owner = await _setup(db, seeded, "22", signed=True)
    await _indep_user(db, seeded, "qa.met22", "QA Releaser")
    token = await login(client, "admin.met22")
    releaser_token = await login(client, "qa.met22")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)

    resp = await client.post(
        f"/quality-metrics/v1/definitions/{definition_id}/signature-challenges", json={"action": "release"},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Released"

    resp = await _release(
        client, releaser_token, definition_id, 1, challenge_id=body["challenge_id"], reauth_password=DEMO_PASSWORD,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


async def test_snapshot_signature_challenge_404_for_missing_snapshot(client, seeded, db):
    owner = await _setup(db, seeded, "23")
    token = await login(client, "admin.met23")
    resp = await client.post(
        "/quality-metrics/v1/management-review-packages/signature-challenges",
        json={"action": "management_review", "snapshot_ids": [str(uuid.uuid4())]}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_snapshot_signature_challenge_requires_nonempty_snapshot_ids(client, seeded, db):
    owner = await _setup(db, seeded, "24")
    token = await login(client, "admin.met24")
    resp = await client.post(
        "/quality-metrics/v1/management-review-packages/signature-challenges",
        json={"action": "management_review", "snapshot_ids": []}, headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_snapshot_signature_challenge_round_trip_signs_management_review(client, seeded, db):
    # release_signed=False: release must succeed unsigned so the test can reach a COMPLETE snapshot;
    # review_signed=True is the actual behaviour under test.
    owner = await _setup(db, seeded, "25", release_signed=False, review_signed=True)
    await _indep_user(db, seeded, "qa.met25", "QA Reviewer")
    token = await login(client, "admin.met25")
    reviewer_token = await login(client, "qa.met25")
    definition_id = await _create_definition(client, token, seeded["site_id"], owner.id)
    assert (await _release(client, token, definition_id, 1)).status_code == 200
    resp = await _calculate(client, token, seeded["site_id"], definition_id)
    assert resp.status_code == 200, resp.text
    snapshot_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/quality-metrics/v1/management-review-packages/signature-challenges",
        json={"action": "management_review", "snapshot_ids": [snapshot_id]}, headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Reviewed"

    resp = await _freeze_package(
        client, reviewer_token, seeded["site_id"], [snapshot_id],
        challenge_id=body["challenge_id"], reauth_password=DEMO_PASSWORD,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
