"""Document 29 (SPEC-QMS-004) -- the buildable slice: the linear DRAFT -> IMPACT_ASSESSMENT -> APPROVAL ->
IMPLEMENTATION -> VERIFICATION -> EFFECTIVE -> CLOSED pipeline plus an emergency lane (DRAFT/
IMPACT_ASSESSMENT -> IMPLEMENTATION directly, retrospective review via approve() afterward) and CANCELLED
(via close()'s cancellation_reason), matching the module's own 8-op API list exactly. New module.
CHG-FR-004(partial)/009(partial)/015(partial)/019/022/023/024 are out of scope this pass -- see
docs/generated/18_SPEC_GAPS.md SG-071/SG-072/SG-073.
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
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.chg{tag}")
        # SG-138 (2026-09-10): Document 106 section 9 rows 86/87/88 -- approve `Approved` by a
        # "QA Releaser" independent of the author, verify `Verified` by a qualified independent verifier
        # (no role), close `Approved` by a "QA Releaser" independent of the investigator/owner.
        for action, meaning, role in (
            ("approve", "Approved", "QA Releaser"),
            ("verify", "Verified", None),
            ("close", "Approved", "QA Releaser"),
        ):
            db.add(SignaturePolicy(
                record_type="change_control", action=action, meaning=meaning, signature_required=signed,
                required_role_id=(seeded["roles"][role].id if (signed and role) else None),
                requires_independent_signer=signed,
            ))
    return owner


async def _indep_qa_releaser(db, seeded, username):
    """A QA Releaser who is not the change control's owner (Document 106 section 9 independence)."""
    async with db.begin():
        user = User(
            username=username, email=f"{username}@example.com", full_name="Indep QA Releaser",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
    return user


def _create_body(site_id, owner_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "change_number": f"CHG-{uuid.uuid4().hex[:8]}",
        "change_type": "recipe", "classification": "permanent", "current_state": {"step_count": 5},
        "proposed_state": {"step_count": 6}, "reason": "add an additional filtration step",
        "owner_subject_id": str(owner_id),
    }
    body.update(overrides)
    return body


async def _create(client, token, site_id, owner_id, **overrides):
    resp = await client.post("/qms/v1/changes", json=_create_body(site_id, owner_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


COMPLETE_IMPACT = {
    "idempotency_key": None, "change_id": None, "expected_version": None,
    "regulatory_impact": {"requires_review": False},
    "validation_impact": {"required": True},
    "training_impact": {"required": True},
    "impact_assessment": {"quality_impact": "minor", "open_batch_impact": "none", "data_migration_impact": "none"},
}


def _impact_body(change_id, expected_version, **overrides):
    body = dict(COMPLETE_IMPACT)
    body.update({"idempotency_key": idem(), "change_id": change_id, "expected_version": expected_version})
    body.update(overrides)
    return body


async def _advance_to_verification(client, token, change_id, owner_id, **impact_overrides):
    """create() already called; change.version == 1. Returns the next expected_version once VERIFICATION
    is reached (ready to pass into make-effective())."""
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact", json=_impact_body(change_id, 1, **impact_overrides), headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 1 -> 2

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 2, "approval_notes": "approved for implementation"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 2 -> 3

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/implement",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 3},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 3 -> 4

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/tasks",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": 4,
            "description": "update work instruction WI-014", "owner_subject_id": str(owner_id),
            "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 4 -> 5

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/verify",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": 5,
            "verification_evidence": {"result": "pass", "verified_by": str(owner_id)},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 5 -> 6
    return 6


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/changes", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_rejects_unrecognized_change_type(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.chg1")
    resp = await client.post(
        "/qms/v1/changes", json=_create_body(seeded["site_id"], owner.id, change_type="not_a_real_type"), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_full_lifecycle_to_closed(client, seeded, db):
    owner = await _setup(db, seeded, "2", signed=False)
    token = await login(client, "admin.chg2")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_verification(client, token, change_id, owner.id)

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/make-effective",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": next_version,
            "effective_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), "training_confirmed": True,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/close",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": next_version, "post_implementation_review": {}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "EFFECTIVE_DATE_BLOCKED"

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/close",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": next_version,
            "post_implementation_review": {"conclusion": "intended result achieved, no adverse effect"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_impact_incomplete_blocks_approval(client, seeded, db):
    owner = await _setup(db, seeded, "3")
    token = await login(client, "admin.chg3")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact",
        json=_impact_body(change_id, 1, training_impact=None),
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 2},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "CHANGE_IMPACT_INCOMPLETE"


async def test_regulatory_review_required(client, seeded, db):
    owner = await _setup(db, seeded, "4")
    token = await login(client, "admin.chg4")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact",
        json=_impact_body(change_id, 1, regulatory_impact={"requires_review": True}),
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 2},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "REGULATORY_REVIEW_REQUIRED"


async def test_implement_without_approval_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "5")
    token = await login(client, "admin.chg5")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/implement",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "CHANGE_NOT_APPROVED"


async def test_emergency_change_implements_directly_then_retrospective_review(client, seeded, db):
    owner = await _setup(db, seeded, "6")
    token = await login(client, "admin.chg6")
    change_id = await _create(client, token, seeded["site_id"], owner.id, emergency=True, emergency_reason="line-down contamination risk")

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/implement",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # emergency bypass -- no CHANGE_NOT_APPROVED

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 2},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text  # retrospective_findings required
    assert resp.json()["code"] == "VALIDATION_FAILED"

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": 2,
            "retrospective_findings": {"conclusion": "emergency justified, no adverse effect found"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms.change_models import ChangeControl
    change = await db.get(ChangeControl, uuid.UUID(change_id))
    assert change.retrospective_review_completed is True
    assert change.state == "IMPLEMENTATION"  # retrospective review does not itself advance state


async def test_validation_incomplete_blocks_verify(client, seeded, db):
    owner = await _setup(db, seeded, "7")
    token = await login(client, "admin.chg7")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact", json=_impact_body(change_id, 1, validation_impact={"required": True}), headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 2},
        headers=auth_headers(token),
    )
    await client.post(
        f"/qms/v1/changes/{change_id}/implement",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 3},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/verify",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 4},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "VALIDATION_INCOMPLETE"


async def test_training_incomplete_blocks_make_effective(client, seeded, db):
    owner = await _setup(db, seeded, "8")
    token = await login(client, "admin.chg8")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_verification(client, token, change_id, owner.id, training_impact={"required": True})
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/make-effective",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": next_version,
            "effective_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "TRAINING_INCOMPLETE"


async def test_effective_date_in_past_blocked(client, seeded, db):
    owner = await _setup(db, seeded, "9")
    token = await login(client, "admin.chg9")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_verification(client, token, change_id, owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/make-effective",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": next_version,
            "effective_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), "training_confirmed": True,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "EFFECTIVE_DATE_BLOCKED"


async def test_cancellation(client, seeded, db):
    owner = await _setup(db, seeded, "10", signed=False)
    token = await login(client, "admin.chg10")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/close",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 1, "cancellation_reason": "requirement superseded by CHG-0099"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    from app.modules.qms.change_models import ChangeControl
    change = await db.get(ChangeControl, uuid.UUID(change_id))
    assert change.state == "CANCELLED"
    assert change.cancel_reason == "requirement superseded by CHG-0099"


async def test_approve_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "11", signed=True)
    await _indep_qa_releaser(db, seeded, "qa.chg11")
    token = await login(client, "admin.chg11")
    signer_token = await login(client, "qa.chg11")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact", json=_impact_body(change_id, 1), headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    # Independent QA Releaser, correct role, no challenge -> still MISSING_SIGNATURE.
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={"idempotency_key": idem(), "change_id": change_id, "expected_version": 2},
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_approve_by_the_change_owner_is_refused_as_not_independent(client, seeded, db):
    """Document 106 section 9 row 86: `change_control/approve` must be independent of the author. The
    change owner holding QA Releaser still cannot sign their own approval."""
    await _setup(db, seeded, "11b", signed=True)
    qa_owner = await _indep_qa_releaser(db, seeded, "qa.chg11b")
    token = await login(client, "admin.chg11b")
    qa_token = await login(client, "qa.chg11b")
    change_id = await _create(client, token, seeded["site_id"], qa_owner.id)
    await client.post(f"/qms/v1/changes/{change_id}/impact", json=_impact_body(change_id, 1), headers=auth_headers(token))
    challenge = (
        await client.post(
            f"/qms/v1/changes/{change_id}/signature-challenges", json={"action": "approve"}, headers=auth_headers(qa_token),
        )
    ).json()
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": 2, "approval_notes": "self-approve",
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SOD_INDEPENDENCE_REQUIRED"


async def test_close_fails_closed_when_signature_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.chg12")
        db.add(SignaturePolicy(record_type="change_control", action="approve", meaning="Approved", signature_required=False))
        db.add(SignaturePolicy(record_type="change_control", action="verify", meaning="Approved", signature_required=False))
        # Deliberately no SignaturePolicy(record_type="change_control", action="close", ...) row.
    token = await login(client, "admin.chg12")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _advance_to_verification(client, token, change_id, owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/make-effective",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": next_version,
            "effective_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(), "training_confirmed": True,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/close",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": next_version,
            "post_implementation_review": {"conclusion": "done"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "13")
    token = await login(client, "admin.chg13")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact", json=_impact_body(change_id, 99), headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "14")
    token = await login(client, "admin.chg14")
    key = idem()
    body = _create_body(seeded["site_id"], owner.id)
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/changes", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/changes", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_duplicate_idempotency_key_different_payload_conflicts(client, seeded, db):
    owner = await _setup(db, seeded, "15")
    token = await login(client, "admin.chg15")
    key = idem()
    body1 = _create_body(seeded["site_id"], owner.id, change_number="CHG-IDEM-A")
    body1["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/changes", json=body1, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    body2 = _create_body(seeded["site_id"], owner.id, change_number="CHG-IDEM-B")
    body2["idempotency_key"] = key
    resp2 = await client.post("/qms/v1/changes", json=body2, headers=auth_headers(token))
    assert resp2.status_code == 409, resp2.text
    assert resp2.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_affected_objects_recorded(client, seeded, db):
    owner = await _setup(db, seeded, "16")
    token = await login(client, "admin.chg16")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    recipe_id = str(uuid.uuid4())
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact",
        json=_impact_body(change_id, 1, affected_objects=[
            {"object_type": "recipe_version", "object_id": recipe_id, "object_version": 3, "impact_category": "direct", "action_required": "re-release recipe version"},
        ]),
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    from app.modules.qms import change_service
    objs = await change_service.get_affected_objects(db, uuid.UUID(change_id))
    assert len(objs) == 1
    assert str(objs[0].object_id) == recipe_id
    assert objs[0].object_version == 3


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.chg20")
    token = await login(client, "admin.chg20")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/signature-challenges", json={"action": "approve"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_change(client, seeded, db):
    owner = await _setup(db, seeded, "21")
    token = await login(client, "admin.chg21")
    resp = await client.post(
        f"/qms/v1/changes/{uuid.uuid4()}/signature-challenges", json={"action": "approve"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_approve(client, seeded, db):
    owner = await _setup(db, seeded, "22", signed=True)
    await _indep_qa_releaser(db, seeded, "qa.chg22")
    token = await login(client, "admin.chg22")
    signer_token = await login(client, "qa.chg22")
    change_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/changes/{change_id}/impact", json=_impact_body(change_id, 1), headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 1 -> 2

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/signature-challenges", json={"action": "approve"}, headers=auth_headers(signer_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Approved"

    resp = await client.post(
        f"/qms/v1/changes/{change_id}/approve",
        json={
            "idempotency_key": idem(), "change_id": change_id, "expected_version": 2, "approval_notes": "approved for implementation",
            "challenge_id": body["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
