"""Document 27 (SPEC-QMS-002) -- the buildable slice: the linear OPEN -> PLAN -> IMPLEMENTATION ->
IMPLEMENTATION_VERIFIED -> EFFECTIVENESS_MONITORING -> EFFECTIVENESS_REVIEW -> CLOSED pipeline plus
EFFECTIVENESS_FAILED -> REOPENED/IMPLEMENTATION and CLOSED -> REOPENED, matching the module's own 8-op API
list exactly. New module. CAPA-FR-008(partial)/014/020/021(partial)/022 are out of scope this pass -- see
docs/generated/18_SPEC_GAPS.md SG-063/SG-064/SG-065 and the existing SG-062.
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.qms.models import DeviationRecord
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
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.capa{tag}")
        # SG-138 (2026-09-10): when the close signature is required, it carries Document 106 section 9
        # row 80's real values -- signed by a "QA Releaser" independent of the CAPA owner.
        db.add(SignaturePolicy(
            record_type="capa_record", action="close", meaning="Approved", signature_required=signed,
            required_role_id=seeded["roles"]["QA Releaser"].id if signed else None,
            requires_independent_signer=signed,
        ))
        # SG-210 (2026-09-18, project-owner-directed): same shape as close above, only enforced on
        # record_effectiveness()'s "recording a result" branch.
        db.add(SignaturePolicy(
            record_type="capa_record", action="effectiveness", meaning="Approved", signature_required=signed,
            required_role_id=seeded["roles"]["QA Releaser"].id if signed else None,
            requires_independent_signer=signed,
        ))
        # Known-limitations fix (docs/testing/demo-gujarati/10 §10.6 item 3): create_capa now
        # FK-validates source_id against a real record for source_type="deviation" -- give every test a
        # real DeviationRecord to point at instead of an arbitrary UUID.
        deviation = DeviationRecord(
            site_id=seeded["site_id"], deviation_number=f"DEV-CAPA-TEST-{tag}-{uuid.uuid4().hex[:6]}",
            deviation_type="process", source_type="batch", source_id=uuid.uuid4(),
            severity="major", owner_subject_id=owner.id, state="OPEN",
        )
        db.add(deviation)
        await db.flush()
        seeded["_capa_source_deviation_id"] = deviation.id
    return owner


async def _indep_qa_releaser(db, seeded, username):
    """A QA Releaser who is not the CAPA owner -- the independent signer Document 106 section 9 row 80
    requires for `capa_record/close`."""
    async with db.begin():
        user = User(
            username=username, email=f"{username}@example.com", full_name="Indep QA Releaser",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
    return user


def _create_body(seeded, owner_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "capa_number": f"CAPA-{uuid.uuid4().hex[:8]}",
        "source_type": "deviation", "source_id": str(seeded["_capa_source_deviation_id"]),
        "problem_statement": "recurring seal failure on line 2",
        "risk_class": "high", "owner_subject_id": str(owner_id),
        "target_date": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "root_cause_ref": {"investigation_ref": str(uuid.uuid4())},
    }
    body.update(overrides)
    return body


async def _create(client, token, seeded, owner_id, **overrides):
    resp = await client.post("/qms/v1/capas", json=_create_body(seeded, owner_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _advance_to_effectiveness_review(client, db, token, capa_id, owner_id, *, effectiveness_signer_token=None):
    """create() already called; capa.version == 1. Returns the capa's expected_version once
    EFFECTIVENESS_REVIEW is reached (ready to pass straight into close()).

    `effectiveness_signer_token`: SG-210 (2026-09-18) -- pass this when the caller's `_setup(signed=True)`
    made `capa_record/effectiveness` signature-required, so "record result" is signed by an independent
    QA Releaser instead of `token` (which is usually the CAPA owner and would fail either the required
    role or the independence check). Leave unset when the policy is unsigned."""
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/plan",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 1,
            "corrective_action": {"description": "replace seal supplier and add incoming inspection"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 1 -> 2

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/actions",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 2, "action_type": "corrective",
            "description": "qualify new seal supplier", "owner_subject_id": str(owner_id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=14)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 2 -> 3
    from app.modules.qms import capa_service
    actions = await capa_service.get_actions(db, uuid.UUID(capa_id))
    action_id = str(actions[0].id)

    resp = await client.post(
        f"/qms/v1/actions/{action_id}/complete",
        json={
            "idempotency_key": idem(), "action_id": action_id, "expected_version": 1,
            "implementation_evidence": {"description": "new supplier qualified, PO placed", "evidence_refs": ["DOC-1"]},
            "verified_by": str(owner_id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # capa version 3 -> 4 (last open action)

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/effectiveness",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 4,
            "criterion": "seal failure rate < 0.1% over 90 days", "data_source": "QC incoming inspection log",
            "observation_start": datetime.now(timezone.utc).isoformat(),
            "observation_end": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=91)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 4 -> 5
    checks = await capa_service.get_effectiveness_checks(db, uuid.UUID(capa_id))
    check_id = str(checks[0].id)

    result_body = {
        "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 5, "check_id": check_id,
        "result": "pass", "evidence": {"observed_rate": "0.02%"},
    }
    signer_token = token
    if effectiveness_signer_token is not None:
        signer_token = effectiveness_signer_token
        challenge = (
            await client.post(
                f"/qms/v1/capas/{capa_id}/signature-challenges", json={"action": "effectiveness"},
                headers=auth_headers(signer_token),
            )
        ).json()
        result_body["challenge_id"] = challenge["challenge_id"]
        result_body["reauth_password"] = DEMO_PASSWORD

    resp = await client.post(f"/qms/v1/capas/{capa_id}/effectiveness", json=result_body, headers=auth_headers(signer_token))
    assert resp.status_code == 200, resp.text  # version 5 -> 6
    return 6


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/capas", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_rejects_unrecognized_source_type(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.capa1")
    resp = await client.post(
        "/qms/v1/capas", json=_create_body(seeded, owner.id, source_type="not_a_real_source"), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "CAPA_SOURCE_REQUIRED"


async def test_create_rejects_nonexistent_source_id(client, seeded, db):
    """Known-limitations fix (docs/testing/demo-gujarati/10 §10.6 item 3): source_id must reference a
    real record for source_type="deviation" -- an arbitrary UUID is no longer accepted."""
    owner = await _setup(db, seeded, "1b")
    token = await login(client, "admin.capa1b")
    resp = await client.post(
        "/qms/v1/capas", json=_create_body(seeded, owner.id, source_id=str(uuid.uuid4())), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_create_requires_root_cause_ref(client, seeded, db):
    owner = await _setup(db, seeded, "2")
    token = await login(client, "admin.capa2")
    resp = await client.post(
        "/qms/v1/capas", json=_create_body(seeded, owner.id, root_cause_ref={}), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "CAPA_ROOT_CAUSE_REQUIRED"


async def test_create_captures_scope_and_recurrence_links(client, seeded, db):
    owner = await _setup(db, seeded, "2b")
    token = await login(client, "admin.capa2b")
    prior_capa_id = str(uuid.uuid4())
    capa_id = await _create(
        client, token, seeded, owner.id,
        scope_type="enterprise", scope_refs=[{"product_id": str(uuid.uuid4())}],
        recurrence_links=[{"quality_event_type": "capa", "quality_event_id": prior_capa_id}],
    )
    from app.modules.qms.capa_models import CapaRecord
    capa = await db.get(CapaRecord, uuid.UUID(capa_id))
    assert capa.scope_type == "enterprise"
    assert capa.scope_refs[0]["product_id"]
    assert capa.recurrence_links[0]["quality_event_id"] == prior_capa_id


async def test_full_lifecycle_to_closed(client, seeded, db):
    owner = await _setup(db, seeded, "3", signed=False)
    token = await login(client, "admin.capa3")
    capa_id = await _create(client, token, seeded, owner.id)
    next_version = await _advance_to_effectiveness_review(client, db, token, capa_id, owner.id)

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/close",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": next_version, "conclusion": ""},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "CAPA_CLOSURE_BLOCKED"

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/close",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": next_version,
            "conclusion": "Effectiveness confirmed; CAPA closed.",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_close_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "4", signed=True)
    await _indep_qa_releaser(db, seeded, "qa.capa4")
    token = await login(client, "admin.capa4")
    signer_token = await login(client, "qa.capa4")
    capa_id = await _create(client, token, seeded, owner.id)
    next_version = await _advance_to_effectiveness_review(
        client, db, token, capa_id, owner.id, effectiveness_signer_token=signer_token
    )
    # Independent QA Releaser, correct role, but no challenge -> still MISSING_SIGNATURE.
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/close",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": next_version, "conclusion": "done"},
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_close_fails_closed_when_signature_policy_unresolved(client, seeded, db):
    owner = await _make_admin_no_policy(db, seeded, "5")
    token = await login(client, "admin.capa5")
    capa_id = await _create(client, token, seeded, owner.id)
    next_version = await _advance_to_effectiveness_review(client, db, token, capa_id, owner.id)
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/close",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": next_version, "conclusion": "done"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def _make_admin_no_policy(db, seeded, tag):
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.capa{tag}")
        # Deliberately no SignaturePolicy(record_type="capa_record", action="close", ...) row -- this is
        # what test_close_fails_closed_when_signature_policy_unresolved exercises. "effectiveness" gets
        # an explicit unsigned row so _advance_to_effectiveness_review() can still reach the "close" step
        # this helper's callers actually want to test.
        db.add(SignaturePolicy(record_type="capa_record", action="effectiveness", meaning="Approved", signature_required=False))
        deviation = DeviationRecord(
            site_id=seeded["site_id"], deviation_number=f"DEV-CAPA-TEST-{tag}-{uuid.uuid4().hex[:6]}",
            deviation_type="process", source_type="batch", source_id=uuid.uuid4(),
            severity="major", owner_subject_id=owner.id, state="OPEN",
        )
        db.add(deviation)
        await db.flush()
        seeded["_capa_source_deviation_id"] = deviation.id
    return owner


async def test_action_evidence_required_to_complete(client, seeded, db):
    owner = await _setup(db, seeded, "6")
    token = await login(client, "admin.capa6")
    capa_id = await _create(client, token, seeded, owner.id)
    await client.post(
        f"/qms/v1/capas/{capa_id}/plan",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": 1, "corrective_action": {"description": "fix it"}},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/actions",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 2, "action_type": "corrective",
            "description": "do the fix", "owner_subject_id": str(owner.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    from app.modules.qms import capa_service
    actions = await capa_service.get_actions(db, uuid.UUID(capa_id))
    action_id = str(actions[0].id)

    resp = await client.post(
        f"/qms/v1/actions/{action_id}/complete",
        json={"idempotency_key": idem(), "action_id": action_id, "expected_version": 1, "implementation_evidence": {}, "verified_by": str(owner.id)},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "ACTION_EVIDENCE_REQUIRED"


async def test_action_dependency_open_blocks_completion(client, seeded, db):
    owner = await _setup(db, seeded, "7")
    token = await login(client, "admin.capa7")
    capa_id = await _create(client, token, seeded, owner.id)
    await client.post(
        f"/qms/v1/capas/{capa_id}/plan",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": 1, "corrective_action": {"description": "fix it"}},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/actions",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 2, "action_type": "corrective",
            "description": "step 1", "owner_subject_id": str(owner.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    from app.modules.qms import capa_service
    step1 = (await capa_service.get_actions(db, uuid.UUID(capa_id)))[0]

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/actions",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 3, "action_type": "corrective",
            "description": "step 2, depends on step 1", "owner_subject_id": str(owner.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat(),
            "dependency_links": [{"dependency_type": "capa_action", "reference_id": str(step1.id)}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    step2 = [a for a in await capa_service.get_actions(db, uuid.UUID(capa_id)) if a.id != step1.id][0]

    resp = await client.post(
        f"/qms/v1/actions/{step2.id}/complete",
        json={
            "idempotency_key": idem(), "action_id": str(step2.id), "expected_version": 1,
            "implementation_evidence": {"description": "done"}, "verified_by": str(owner.id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "ACTION_DEPENDENCY_OPEN"


async def test_effectiveness_result_requires_a_defined_check(client, seeded, db):
    owner = await _setup(db, seeded, "8")
    token = await login(client, "admin.capa8")
    capa_id = await _create(client, token, seeded, owner.id)
    await client.post(
        f"/qms/v1/capas/{capa_id}/plan",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": 1, "corrective_action": {"description": "fix it"}},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/actions",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 2, "action_type": "corrective",
            "description": "do the fix", "owner_subject_id": str(owner.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        headers=auth_headers(token),
    )
    from app.modules.qms import capa_service
    actions = await capa_service.get_actions(db, uuid.UUID(capa_id))
    await client.post(
        f"/qms/v1/actions/{actions[0].id}/complete",
        json={
            "idempotency_key": idem(), "action_id": str(actions[0].id), "expected_version": 1,
            "implementation_evidence": {"description": "done"}, "verified_by": str(owner.id),
        },
        headers=auth_headers(token),
    )
    # capa is now IMPLEMENTATION_VERIFIED, version 4 -- define a check to enter EFFECTIVENESS_MONITORING,
    # then attempt to record a result with no check_id (the reachable trigger for EFFECTIVENESS_PLAN_REQUIRED:
    # the state guard itself already makes "record a result before ever defining a check" unreachable,
    # since only defining a check can transition into EFFECTIVENESS_MONITORING in the first place).
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/effectiveness",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 4,
            "criterion": "no recurrence over 90 days", "data_source": "QC log",
            "observation_start": datetime.now(timezone.utc).isoformat(),
            "observation_end": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=91)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/effectiveness",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": 5, "result": "pass", "evidence": {"x": "y"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "EFFECTIVENESS_PLAN_REQUIRED"


async def test_failed_effectiveness_then_reopen(client, seeded, db):
    owner = await _setup(db, seeded, "9")
    token = await login(client, "admin.capa9")
    capa_id = await _create(client, token, seeded, owner.id)
    await client.post(
        f"/qms/v1/capas/{capa_id}/plan",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": 1, "corrective_action": {"description": "fix it"}},
        headers=auth_headers(token),
    )
    await client.post(
        f"/qms/v1/capas/{capa_id}/actions",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 2, "action_type": "corrective",
            "description": "do the fix", "owner_subject_id": str(owner.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        headers=auth_headers(token),
    )
    from app.modules.qms import capa_service
    actions = await capa_service.get_actions(db, uuid.UUID(capa_id))
    await client.post(
        f"/qms/v1/actions/{actions[0].id}/complete",
        json={
            "idempotency_key": idem(), "action_id": str(actions[0].id), "expected_version": 1,
            "implementation_evidence": {"description": "done"}, "verified_by": str(owner.id),
        },
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/effectiveness",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 4,
            "criterion": "no recurrence over 90 days", "data_source": "QC log",
            "observation_start": datetime.now(timezone.utc).isoformat(),
            "observation_end": (datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=91)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    checks = await capa_service.get_effectiveness_checks(db, uuid.UUID(capa_id))
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/effectiveness",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 5, "check_id": str(checks[0].id),
            "result": "fail", "evidence": {"observed_rate": "2%"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms.capa_models import CapaRecord
    capa = await db.get(CapaRecord, uuid.UUID(capa_id))
    assert capa.state == "EFFECTIVENESS_FAILED"

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/reopen",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 6,
            "reason": "effectiveness check failed", "new_evidence": "recurrence observed in QC log",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    await db.refresh(capa)
    assert capa.state == "REOPENED"
    assert len(capa.reopen_history) == 1


async def test_cancellation(client, seeded, db):
    owner = await _setup(db, seeded, "10", signed=False)
    token = await login(client, "admin.capa10")
    capa_id = await _create(client, token, seeded, owner.id)
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/close",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 1,
            "cancellation_reason": "duplicate of CAPA-0001",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    from app.modules.qms.capa_models import CapaRecord
    capa = await db.get(CapaRecord, uuid.UUID(capa_id))
    assert capa.state == "CANCELLED"
    assert capa.cancel_reason == "duplicate of CAPA-0001"


async def test_extend_retains_old_target_date(client, seeded, db):
    owner = await _setup(db, seeded, "11")
    token = await login(client, "admin.capa11")
    capa_id = await _create(client, token, seeded, owner.id)
    new_target = (datetime.now(timezone.utc) + timedelta(days=60)).isoformat()
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/extend",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 1, "new_target_date": new_target,
            "reason": "awaiting supplier qualification", "risk_review": "no product impact from delay",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    from app.modules.qms.capa_models import CapaRecord
    capa = await db.get(CapaRecord, uuid.UUID(capa_id))
    assert len(capa.extension_history) == 1
    assert capa.target_date.isoformat().startswith(new_target[:10])


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "12")
    token = await login(client, "admin.capa12")
    capa_id = await _create(client, token, seeded, owner.id)
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/plan",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": 99, "corrective_action": {"description": "x"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "13")
    token = await login(client, "admin.capa13")
    key = idem()
    body = _create_body(seeded, owner.id)
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/capas", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/capas", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_duplicate_idempotency_key_different_payload_conflicts(client, seeded, db):
    owner = await _setup(db, seeded, "14")
    token = await login(client, "admin.capa14")
    key = idem()
    body1 = _create_body(seeded, owner.id, capa_number="CAPA-IDEM-A")
    body1["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/capas", json=body1, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    body2 = _create_body(seeded, owner.id, capa_number="CAPA-IDEM-B")
    body2["idempotency_key"] = key
    resp2 = await client.post("/qms/v1/capas", json=body2, headers=auth_headers(token))
    assert resp2.status_code == 409, resp2.text
    assert resp2.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_multi_action_capa_requires_all_actions_completed_before_verified(client, seeded, db):
    owner = await _setup(db, seeded, "15")
    token = await login(client, "admin.capa15")
    capa_id = await _create(client, token, seeded, owner.id)
    await client.post(
        f"/qms/v1/capas/{capa_id}/plan",
        json={"idempotency_key": idem(), "capa_id": capa_id, "expected_version": 1, "corrective_action": {"description": "fix it"}, "preventive_action": {"description": "broader process change"}},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/actions",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 2, "action_type": "corrective",
            "description": "action A", "owner_subject_id": str(owner.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 2 -> 3
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/actions",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": 3, "action_type": "preventive",
            "description": "action B", "owner_subject_id": str(owner.id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=20)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 3 -> 4 (stays IMPLEMENTATION, not yet VERIFIED)

    from app.modules.qms import capa_service
    from app.modules.qms.capa_models import CapaRecord
    actions = await capa_service.get_actions(db, uuid.UUID(capa_id))
    assert len(actions) == 2

    await client.post(
        f"/qms/v1/actions/{actions[0].id}/complete",
        json={
            "idempotency_key": idem(), "action_id": str(actions[0].id), "expected_version": 1,
            "implementation_evidence": {"description": "done A"}, "verified_by": str(owner.id),
        },
        headers=auth_headers(token),
    )
    capa = await db.get(CapaRecord, uuid.UUID(capa_id))
    assert capa.state == "IMPLEMENTATION"  # one action still open

    await client.post(
        f"/qms/v1/actions/{actions[1].id}/complete",
        json={
            "idempotency_key": idem(), "action_id": str(actions[1].id), "expected_version": 1,
            "implementation_evidence": {"description": "done B"}, "verified_by": str(owner.id),
        },
        headers=auth_headers(token),
    )
    await db.refresh(capa)
    assert capa.state == "IMPLEMENTATION_VERIFIED"


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    owner = await _make_admin_no_policy(db, seeded, "24")
    token = await login(client, "admin.capa24")
    capa_id = await _create(client, token, seeded, owner.id)
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_capa(client, seeded, db):
    owner = await _setup(db, seeded, "25")
    token = await login(client, "admin.capa25")
    resp = await client.post(
        f"/qms/v1/capas/{uuid.uuid4()}/signature-challenges", json={"action": "close"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_close(client, seeded, db):
    owner = await _setup(db, seeded, "26", signed=True)
    await _indep_qa_releaser(db, seeded, "qa.capa26")
    token = await login(client, "admin.capa26")
    signer_token = await login(client, "qa.capa26")
    capa_id = await _create(client, token, seeded, owner.id)
    next_version = await _advance_to_effectiveness_review(
        client, db, token, capa_id, owner.id, effectiveness_signer_token=signer_token
    )

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(signer_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Approved"

    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/close",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": next_version,
            "conclusion": "Effectiveness confirmed; CAPA closed.",
            "challenge_id": body["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


async def test_close_by_the_capa_owner_is_refused_as_not_independent(client, seeded, db):
    """Document 106 section 9 row 80: `capa_record/close` MUST be independent of the investigator/owner
    (Document 107 SOD-006 shape). The CAPA owner holding QA Releaser still cannot sign their own close."""
    await _setup(db, seeded, "27", signed=True)
    qa_owner = await _indep_qa_releaser(db, seeded, "qa.capa27")
    # A second independent QA Releaser to sign the effectiveness-result step -- qa_owner is disqualified
    # (they're the CAPA owner) and admin doesn't hold the QA Releaser role required_role_id names.
    await _indep_qa_releaser(db, seeded, "qa.capa27b")
    effectiveness_signer_token = await login(client, "qa.capa27b")
    token = await login(client, "admin.capa27")
    qa_token = await login(client, "qa.capa27")
    capa_id = await _create(client, token, seeded, qa_owner.id)
    next_version = await _advance_to_effectiveness_review(
        client, db, token, capa_id, qa_owner.id, effectiveness_signer_token=effectiveness_signer_token
    )
    challenge = (
        await client.post(
            f"/qms/v1/capas/{capa_id}/signature-challenges", json={"action": "close"}, headers=auth_headers(qa_token),
        )
    ).json()
    resp = await client.post(
        f"/qms/v1/capas/{capa_id}/close",
        json={
            "idempotency_key": idem(), "capa_id": capa_id, "expected_version": next_version, "conclusion": "self-close",
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SOD_INDEPENDENCE_REQUIRED"
