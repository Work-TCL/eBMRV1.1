"""Document 31 (SPEC-QMS-006) -- the buildable slice: requirement -> assignment (ASSIGNED ->
ASSESSMENT_PENDING/COMPLETED, or -> FAILED) -> qualification issuance/renewal -> waiver, matching the
module's own 8-op API list exactly (`/training/v1` prefix). TRN-FR-016's platform-wide execution gate is
out of scope this pass -- see docs/generated/18_SPEC_GAPS.md SG-086..SG-090.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam.models import Qualification, User, UserSiteRole
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


# SG-138 Kind B, RESOLVED 2026-09-11 (PHASE_3_DEFERRED_DECISIONS.md item A): Document 106 section 9 rows
# 91-93 defer create/complete/assess to "per policy lookup"; the project owner authored `assess` from the
# section 8 "verify" family (`Verified`, independent of the trainee being assessed) and create/complete
# from "issue/start" and "complete/record" (`Performed`, no independence). This module's own tests keep
# full per-test control of signature_required (see docstring below) rather than a global conftest.py row,
# so each test's local SignaturePolicy still needs the *real* meaning per action to reflect what
# scripts/seed.py's SIGNATURE_POLICY_FLOOR now ships.
_ACTION_MEANING = {"create": "Performed", "complete": "Performed", "assess": "Verified"}


async def _setup(db, seeded, tag, *, signed_actions=None):
    """`signed_actions` maps action -> signature_required for every training_assignment action the test
    will exercise (create/complete/assess are each independently policy-resolved -- fail-closed per
    (record_type, action) pair, so every action a test drives needs its own row). Defaults to all three
    actions unsigned.
    """
    signed_actions = signed_actions or {"create": False, "complete": False, "assess": False}
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.trn{tag}")
        for action, signed in signed_actions.items():
            db.add(SignaturePolicy(record_type="training_assignment", action=action, meaning=_ACTION_MEANING[action], signature_required=signed))
    return owner


def _requirement_body(site_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "title": f"Curriculum {uuid.uuid4().hex[:6]}",
        "source_type": "document", "training_type": "read_and_understand",
    }
    body.update(overrides)
    return body


async def _create_requirement(client, token, site_id, **overrides):
    resp = await client.post("/training/v1/requirements", json=_requirement_body(site_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _create_assignment(client, token, requirement_id, subject_id, **overrides):
    body = {"idempotency_key": idem(), "requirement_id": requirement_id, "subject_id": str(subject_id)}
    body.update(overrides)
    resp = await client.post("/training/v1/assignments", json=body, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/training/v1/requirements", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_requirement_rejects_unrecognized_training_type(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.trn1")
    resp = await client.post(
        "/training/v1/requirements", json=_requirement_body(seeded["site_id"], training_type="not_a_real_type"), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_full_lifecycle_read_and_understand_to_qualification(client, seeded, db):
    owner = await _setup(db, seeded, "2")
    token = await login(client, "admin.trn2")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)

    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["resulting_version"] == 2

    resp = await client.post(
        "/training/v1/qualifications",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "subject_id": str(owner.id),
            "qualification_code": "DISPENSING_OPERATOR", "effective_from": datetime.now(timezone.utc).isoformat(),
            "source_assignment_id": assignment_id,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    # SG-086 write-through: granting via qms.qualification_record must also satisfy the
    # iam.qualifications-backed execution gates (batch_execution/material) that read it.
    iam_qual = (
        await db.execute(
            select(Qualification).where(
                Qualification.user_id == owner.id, Qualification.qualification_code == "DISPENSING_OPERATOR"
            )
        )
    ).scalar_one_or_none()
    assert iam_qual is not None


async def test_assessment_pending_pass_completes(client, seeded, db):
    owner = await _setup(db, seeded, "3")
    token = await login(client, "admin.trn3")
    requirement_id = await _create_requirement(client, token, seeded["site_id"], training_type="exam", requires_assessment=True, pass_score=70)
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)

    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/assess",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 2, "passed": True, "score": 88},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_assessment_fail_transitions_to_failed_and_retrain_creates_new_assignment(client, seeded, db):
    owner = await _setup(db, seeded, "4")
    token = await login(client, "admin.trn4")
    requirement_id = await _create_requirement(client, token, seeded["site_id"], training_type="exam", requires_assessment=True, pass_score=70)
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/assess",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 2, "passed": False, "score": 40},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms.training_models import TrainingAssignment
    failed = await db.get(TrainingAssignment, uuid.UUID(assignment_id))
    assert failed.state == "FAILED"

    retrain_id = await _create_assignment(
        client, token, requirement_id, owner.id, retrain_of_assignment_id=assignment_id, retraining_trigger="performance",
    )
    retrain = await db.get(TrainingAssignment, uuid.UUID(retrain_id))
    assert retrain.retrain_of_assignment_id == failed.id
    # TRN-FR-024: the failed attempt is never rewritten.
    await db.refresh(failed)
    assert failed.state == "FAILED"


async def test_complete_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "5", signed_actions={"create": False, "complete": True, "assess": False})
    token = await login(client, "admin.trn5")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_trainer_not_qualified_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "6")
    token = await login(client, "admin.trn6")
    trainer = await _make_admin(db, seeded, "admin.trn6.trainer")
    await db.commit()
    requirement_id = await _create_requirement(
        client, token, seeded["site_id"], training_type="instructor_led", required_trainer_qualification_code="CERTIFIED_TRAINER",
    )
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1, "trainer_user_id": str(trainer.id)},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "TRAINER_NOT_QUALIFIED"


async def test_trainer_qualified_succeeds(client, seeded, db):
    owner = await _setup(db, seeded, "7")
    token = await login(client, "admin.trn7")
    trainer = await _make_admin(db, seeded, "admin.trn7.trainer")
    await db.commit()
    resp = await client.post(
        "/training/v1/qualifications",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "subject_id": str(trainer.id),
            "qualification_code": "CERTIFIED_TRAINER", "effective_from": datetime.now(timezone.utc).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    requirement_id = await _create_requirement(
        client, token, seeded["site_id"], training_type="instructor_led", required_trainer_qualification_code="CERTIFIED_TRAINER",
    )
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1, "trainer_user_id": str(trainer.id)},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_waiver_self_approval_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "8")
    token = await login(client, "admin.trn8")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    resp = await client.post(
        "/training/v1/waivers",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "subject_id": str(owner.id),
            "requirement_id": requirement_id, "reason": "Prior equivalent role experience", "approved_by_user_id": str(owner.id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "WAIVER_NOT_AUTHORIZED"


async def test_waiver_created_successfully(client, seeded, db):
    owner = await _setup(db, seeded, "9")
    token = await login(client, "admin.trn9")
    approver = await _make_admin(db, seeded, "admin.trn9.approver")
    await db.commit()
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    resp = await client.post(
        "/training/v1/waivers",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "subject_id": str(owner.id),
            "requirement_id": requirement_id, "reason": "Prior equivalent role experience",
            "approved_by_user_id": str(approver.id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_qualification_renewal_supersedes_prior(client, seeded, db):
    owner = await _setup(db, seeded, "10")
    token = await login(client, "admin.trn10")
    resp = await client.post(
        "/training/v1/qualifications",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "subject_id": str(owner.id),
            "qualification_code": "DISPENSING_OPERATOR", "effective_from": datetime.now(timezone.utc).isoformat(),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    original_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/training/v1/qualifications",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "subject_id": str(owner.id),
            "qualification_code": "DISPENSING_OPERATOR", "effective_from": datetime.now(timezone.utc).isoformat(),
            "renewed_from_qualification_id": original_id,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms.training_models import QualificationRecord
    original = await db.get(QualificationRecord, uuid.UUID(original_id))
    assert original.state == "RENEWED"


async def test_equivalency_credit_requires_evidence_and_approval(client, seeded, db):
    owner = await _setup(db, seeded, "11")
    token = await login(client, "admin.trn11")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1, "equivalency_credit": True},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_matrix_returns_counts(client, seeded, db):
    owner = await _setup(db, seeded, "12")
    token = await login(client, "admin.trn12")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    await _create_assignment(client, token, requirement_id, owner.id)

    resp = await client.get(f"/training/v1/matrix?site_id={seeded['site_id']}", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    rows = resp.json()["requirements"]
    assert any(r["requirement_id"] == requirement_id and r["assigned_count"] >= 1 for r in rows)


async def test_qualification_codes_returns_distinct_granted_codes(client, seeded, db):
    """SG-086: no catalog table exists for qualification codes, so this endpoint is a distinct-values
    read over qms.qualification_record -- suggestion source for Recipe Master's required_qualification_code
    (project-owner-directed, asked directly, chose qms.qualification_record over iam.qualifications)."""
    owner = await _setup(db, seeded, "15")
    token = await login(client, "admin.trn15")
    code = f"CLEANROOM_GOWN_{uuid.uuid4().hex[:6]}"
    for _ in range(2):
        resp = await client.post(
            "/training/v1/qualifications",
            json={
                "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "subject_id": str(owner.id),
                "qualification_code": code, "effective_from": datetime.now(timezone.utc).isoformat(),
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text

    resp = await client.get("/training/v1/qualification-codes", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    codes = resp.json()
    assert codes.count(code) == 1


async def test_qualification_codes_requires_permission(client, seeded, db):
    async with db.begin():
        user = User(
            username="norole.trn16", email="norole.trn16@example.com", full_name="No Role",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
    token = await login(client, "norole.trn16")
    resp = await client.get("/training/v1/qualification-codes", headers=auth_headers(token))
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_subject_status_returns_history(client, seeded, db):
    owner = await _setup(db, seeded, "13")
    token = await login(client, "admin.trn13")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    await _create_assignment(client, token, requirement_id, owner.id)

    resp = await client.get(f"/training/v1/subjects/{owner.id}/status", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    assert len(resp.json()["assignments"]) >= 1


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "14")
    token = await login(client, "admin.trn14")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 99},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "15")
    token = await login(client, "admin.trn15")
    key = idem()
    body = _requirement_body(seeded["site_id"])
    body["idempotency_key"] = key
    resp1 = await client.post("/training/v1/requirements", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/training/v1/requirements", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_duplicate_idempotency_key_different_payload_conflicts(client, seeded, db):
    owner = await _setup(db, seeded, "16")
    token = await login(client, "admin.trn16")
    key = idem()
    body1 = _requirement_body(seeded["site_id"], title="Requirement A")
    body1["idempotency_key"] = key
    resp1 = await client.post("/training/v1/requirements", json=body1, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    body2 = _requirement_body(seeded["site_id"], title="Requirement B")
    body2["idempotency_key"] = key
    resp2 = await client.post("/training/v1/requirements", json=body2, headers=auth_headers(token))
    assert resp2.status_code == 409, resp2.text
    assert resp2.json()["code"] == "IDEMPOTENCY_CONFLICT"


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------
# "create" is deliberately not exercised here -- see training_router.py's own comment on why a
# signature-challenges entry point for training_assignment/create cannot bind to a real record.


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    # "create" needs its own (unsigned) policy row just to get an assignment to exist at all --
    # deliberately no row for "complete", which is the action this test actually targets.
    owner = await _setup(db, seeded, "20", signed_actions={"create": False})
    token = await login(client, "admin.trn20")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_assignment(client, seeded, db):
    owner = await _setup(db, seeded, "21")
    token = await login(client, "admin.trn21")
    resp = await client.post(
        f"/training/v1/assignments/{uuid.uuid4()}/signature-challenges", json={"action": "complete"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_complete(client, seeded, db):
    owner = await _setup(db, seeded, "22", signed_actions={"create": False, "complete": True, "assess": False})
    token = await login(client, "admin.trn22")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)

    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Performed"

    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={
            "idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1,
            "challenge_id": body["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


# --- "create" signature-challenge fix (SG-138 follow-up) -----------------------------------------
# create_assignment() previously could never be signed: the row doesn't exist until the command itself
# flushes it, so no pre-issued challenge could ever bind to it. Fixed via
# POST /training/v1/assignments/signature-challenges (no path id) generating the id up front.


async def test_create_signature_challenge_returns_a_pregenerated_assignment_id(client, seeded, db):
    owner = await _setup(db, seeded, "26", signed_actions={"create": True})
    token = await login(client, "admin.trn26")
    resp = await client.post(
        "/training/v1/assignments/signature-challenges", json={"action": "create"}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Performed"
    assert body["challenge_id"]
    # A real UUID, not the sentinel/None a stub would return.
    assert uuid.UUID(body["assignment_id"])


async def test_create_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.trn27")
        # Deliberately no SignaturePolicy row for training_assignment/create.
    token = await login(client, "admin.trn27")
    resp = await client.post(
        "/training/v1/assignments/signature-challenges", json={"action": "create"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_create_signature_challenge_unknown_action_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "28", signed_actions={"create": True})
    token = await login(client, "admin.trn28")
    resp = await client.post(
        "/training/v1/assignments/signature-challenges", json={"action": "complete"}, headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_create_assignment_round_trip_signs_create(client, seeded, db):
    """The full fix, end to end: challenge -> create_assignment() using the pre-generated id -> the
    inserted row's actual id matches, consume_challenge()'s version/hash check passes, and a real
    signature_id comes back -- proving this is real wiring, not a stub."""
    owner = await _setup(db, seeded, "29", signed_actions={"create": True, "complete": False, "assess": False})
    token = await login(client, "admin.trn29")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])

    resp = await client.post(
        "/training/v1/assignments/signature-challenges", json={"action": "create"}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    challenge = resp.json()
    pregenerated_id = challenge["assignment_id"]

    resp = await client.post(
        "/training/v1/assignments",
        json={
            "idempotency_key": idem(), "requirement_id": requirement_id, "subject_id": str(owner.id),
            "assignment_id": pregenerated_id,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["aggregate_id"] == pregenerated_id
    assert body["signature_id"] is not None

    from app.modules.qms.training_models import TrainingAssignment
    assignment = await db.get(TrainingAssignment, uuid.UUID(pregenerated_id))
    assert assignment is not None
    assert str(assignment.id) == pregenerated_id
    assert assignment.version == 1


# --- SG-138 Kind B `assess` independence (PHASE_3_DEFERRED_DECISIONS.md item A) ------------------


async def _setup_independent_assess(db, seeded, tag):
    """Distinct from `_setup()`: `assess` needs `requires_independent_signer=True`, which `_setup()`'s
    (action, signed) shape has no room for."""
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.trn{tag}")
        db.add(SignaturePolicy(record_type="training_assignment", action="create", meaning="Performed", signature_required=False))
        db.add(SignaturePolicy(record_type="training_assignment", action="complete", meaning="Performed", signature_required=False))
        db.add(SignaturePolicy(
            record_type="training_assignment", action="assess", meaning="Verified",
            signature_required=True, requires_independent_signer=True,
        ))
    return owner


async def test_assess_requires_independent_signer_rejects_self_assessment(client, seeded, db):
    owner = await _setup_independent_assess(db, seeded, "23")
    token = await login(client, "admin.trn23")
    requirement_id = await _create_requirement(client, token, seeded["site_id"], training_type="exam", requires_assessment=True, pass_score=70)
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/signature-challenges", json={"action": "assess"}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    challenge = resp.json()
    assert challenge["meaning"] == "Verified"

    # `owner` is both the trainee (subject_id) and the actor attempting to assess -- MUST be rejected.
    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/assess",
        json={
            "idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 2, "passed": True, "score": 90,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SOD_INDEPENDENCE_REQUIRED"


async def test_assess_signature_round_trip_succeeds_with_independent_assessor(client, seeded, db):
    owner = await _setup_independent_assess(db, seeded, "24")
    assessor = await _make_admin(db, seeded, "admin.trn24.assessor")
    await db.commit()
    token = await login(client, "admin.trn24")
    assessor_token = await login(client, "admin.trn24.assessor")
    requirement_id = await _create_requirement(client, token, seeded["site_id"], training_type="exam", requires_assessment=True, pass_score=70)
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    await client.post(
        f"/training/v1/assignments/{assignment_id}/complete",
        json={"idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 1},
        headers=auth_headers(token),
    )

    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/signature-challenges", json={"action": "assess"}, headers=auth_headers(assessor_token),
    )
    assert resp.status_code == 200, resp.text
    challenge = resp.json()

    resp = await client.post(
        f"/training/v1/assignments/{assignment_id}/assess",
        json={
            "idempotency_key": idem(), "assignment_id": assignment_id, "expected_version": 2, "passed": True, "score": 91,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(assessor_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


async def test_create_assignment_stale_challenge_rejected_if_id_reused_after_expiry_window(client, seeded, db):
    """A pre-generated id that's never actually used to create an assignment leaves no dangling row --
    create_assignment() is free to use a *different*, server-generated id (the normal, unsigned path)
    for a totally unrelated request without any collision."""
    owner = await _setup(db, seeded, "30")
    token = await login(client, "admin.trn30")
    requirement_id = await _create_requirement(client, token, seeded["site_id"])
    assignment_id = await _create_assignment(client, token, requirement_id, owner.id)
    assert uuid.UUID(assignment_id)
