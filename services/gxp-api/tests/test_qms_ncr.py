"""Document 28 (SPEC-QMS-003) -- the buildable slice: the linear OPEN -> SEGREGATED -> EVALUATION ->
{REWORK,REPAIR,RETURN,SCRAP,USE_AS_IS} -> VERIFICATION -> CLOSED pipeline, matching the module's own 6-op
API list exactly. New module. NCR-FR-002/010/011/012(partial)/016/017/018 are out of scope this pass --
see docs/generated/18_SPEC_GAPS.md SG-067/SG-068/SG-069.
"""

import uuid
from datetime import datetime, timezone

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.qms.ncr_models import NonconformanceRecord
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
        owner = await _make_admin(db, seeded, f"admin.ncr{tag}")
        # SG-138 (2026-09-10): Document 106 section 9 rows 83/84/85 -- disposition `Released` by a
        # "QA Releaser", verify `Verified` by a qualified independent verifier (no role), close `Approved`
        # by a "QA Releaser"; all independent of the NCR owner/creator.
        for action, meaning, role in (
            ("disposition", "Released", "QA Releaser"),
            ("verify", "Verified", None),
            ("close", "Approved", "QA Releaser"),
        ):
            db.add(SignaturePolicy(
                record_type="nonconformance_record", action=action, meaning=meaning, signature_required=signed,
                required_role_id=(seeded["roles"][role].id if (signed and role) else None),
                requires_independent_signer=signed,
            ))
    return owner


async def _indep_qa_releaser(db, seeded, username):
    """A QA Releaser who is neither the NCR owner nor its creator (Document 106 section 9 independence)."""
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
        "idempotency_key": idem(), "site_id": str(site_id), "ncr_number": f"NCR-{uuid.uuid4().hex[:8]}",
        "scope_type": "material", "scope_records": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
        "requirement_ref": {"spec_ref": "SPEC-MAT-001"}, "defect_code": "DEF-001", "severity": "major",
        "owner_subject_id": str(owner_id),
    }
    body.update(overrides)
    return body


async def _create(client, token, site_id, owner_id, **overrides):
    resp = await client.post("/qms/v1/nonconformances", json=_create_body(site_id, owner_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _segregate_and_evaluate(client, token, ncr_id):
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/segregate",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": 1, "locations": [{"location": "quarantine cage 3"}]},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 1 -> 2
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/evaluate",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": 2,
            "evaluation": {"usability": "not usable", "quality_impact": "moderate", "safety_impact": "none",
                            "performance_impact": "none", "investigation_needed": False},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text  # version 2 -> 3
    return 3


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/nonconformances", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_requires_scope_records(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.ncr1")
    resp = await client.post(
        "/qms/v1/nonconformances", json=_create_body(seeded["site_id"], owner.id, scope_records=[]), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "NCR_SCOPE_REQUIRED"


async def test_full_lifecycle_return_disposition(client, seeded, db):
    owner = await _setup(db, seeded, "2", signed=False)
    token = await login(client, "admin.ncr2")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "RETURN", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "return to supplier per receiving inspection failure",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "confirmation": {"note": "confirmed returned to supplier"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/close",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "conclusion": ""},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "NCR_CLOSURE_BLOCKED"

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/close",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "conclusion": "Returned to supplier; no further action."},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_rework_requires_route_then_reinspection(client, seeded, db):
    owner = await _setup(db, seeded, "3")
    token = await login(client, "admin.ncr3")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "REWORK", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "reprocess through additional filtration step",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "REWORK_ROUTE_REQUIRED"

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "REWORK", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "reprocess through additional filtration step",
            "rework_route": {"work_instruction_ref": "WI-REWORK-014"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "REINSPECTION_REQUIRED"

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "reinspection_evidence": {"result": "pass", "tested_by": str(owner.id)},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_use_as_is_requires_authorized_by(client, seeded, db):
    owner = await _setup(db, seeded, "4")
    token = await login(client, "admin.ncr4")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "USE_AS_IS", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "cosmetic defect only, no functional impact",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "USE_AS_IS_NOT_AUTHORIZED"

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "USE_AS_IS", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "cosmetic defect only, no functional impact", "use_as_is_authorized_by": str(owner.id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_disposition_capa_required_auto_creates_draft_capa(client, seeded, db):
    """Client gap-closure item #1 (2026-10-09, project-owner-directed): capa_required now auto-creates a
    real OPEN CapaRecord in the same transaction, source_type="ncr", instead of only setting the flag."""
    owner = await _setup(db, seeded, "50")
    token = await login(client, "admin.ncr50")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "RETURN", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "return to supplier per receiving inspection failure",
            "capa_required": True, "capa_rationale": "recurring supplier defect, systemic root cause suspected",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from sqlalchemy import select as _select
    from app.modules.qms.capa_models import CapaRecord
    capas = (await db.execute(_select(CapaRecord).where(CapaRecord.source_type == "ncr", CapaRecord.source_id == uuid.UUID(ncr_id)))).scalars().all()
    assert len(capas) == 1
    capa = capas[0]
    assert capa.state == "OPEN"
    assert capa.owner_subject_id == owner.id  # actor (admin.ncr50, same as owner here) defaults as placeholder owner
    assert capa.risk_class == "pending_assessment"
    assert capa.root_cause_ref["proactive_rationale"] == "recurring supplier defect, systemic root cause suspected"
    assert capa.capa_number.startswith("CAPA-AUTO-")


async def test_disposition_rejects_unrecognized_type(client, seeded, db):
    owner = await _setup(db, seeded, "5")
    token = await login(client, "admin.ncr5")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "NOT_A_REAL_TYPE", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "x",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "DISPOSITION_NOT_ALLOWED"


async def test_disposition_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "6", signed=True)
    await _indep_qa_releaser(db, seeded, "qa.ncr6")
    token = await login(client, "admin.ncr6")
    signer_token = await login(client, "qa.ncr6")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)
    # Independent QA Releaser, correct role, no challenge -> still MISSING_SIGNATURE.
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "SCRAP", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "unrecoverable contamination",
        },
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_disposition_by_the_ncr_owner_is_refused_as_not_independent(client, seeded, db):
    """Document 106 section 9 row 84: `nonconformance_record/disposition` must be independent of every
    production performer on the record. The owner holding QA Releaser still cannot sign it."""
    await _setup(db, seeded, "6b", signed=True)
    qa_owner = await _indep_qa_releaser(db, seeded, "qa.ncr6b")
    token = await login(client, "admin.ncr6b")
    qa_token = await login(client, "qa.ncr6b")
    # admin drives the lifecycle; the NCR's owner_subject_id is the QA Releaser who then tries to sign.
    ncr_id = await _create(client, token, seeded["site_id"], qa_owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)
    challenge = (
        await client.post(
            f"/qms/v1/nonconformances/{ncr_id}/signature-challenges", json={"action": "disposition"},
            headers=auth_headers(qa_token),
        )
    ).json()
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "SCRAP", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "self-disposition attempt",
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SOD_INDEPENDENCE_REQUIRED"


async def test_close_fails_closed_when_signature_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.ncr7")
        db.add(SignaturePolicy(record_type="nonconformance_record", action="disposition", meaning="Approved", signature_required=False))
        db.add(SignaturePolicy(record_type="nonconformance_record", action="verify", meaning="Approved", signature_required=False))
        # Deliberately no SignaturePolicy(record_type="nonconformance_record", action="close", ...) row.
    token = await login(client, "admin.ncr7")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "SCRAP", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "unrecoverable contamination",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "confirmation": {"note": "destroyed per WI-DESTRUCT-2"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/close",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "conclusion": "done"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_partial_scope_multiple_dispositions(client, seeded, db):
    owner = await _setup(db, seeded, "8")
    token = await login(client, "admin.ncr8")
    lot_a, lot_b = str(uuid.uuid4()), str(uuid.uuid4())
    ncr_id = await _create(
        client, token, seeded["site_id"], owner.id,
        scope_records=[{"record_type": "material_lot", "record_id": lot_a}, {"record_type": "material_lot", "record_id": lot_b}],
    )
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "SCRAP", "affected_scope": [{"record_type": "material_lot", "record_id": lot_a}],
            "justification": "lot A unrecoverable",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "RETURN", "affected_scope": [{"record_type": "material_lot", "record_id": lot_b}],
            "justification": "lot B returned to supplier",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    from app.modules.qms import ncr_service
    dispositions = await ncr_service.get_dispositions(db, uuid.UUID(ncr_id))
    assert len(dispositions) == 2
    assert {d.disposition_type for d in dispositions} == {"SCRAP", "RETURN"}


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "9")
    token = await login(client, "admin.ncr9")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/segregate",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": 99, "locations": [{"location": "x"}]},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "10")
    token = await login(client, "admin.ncr10")
    key = idem()
    body = _create_body(seeded["site_id"], owner.id)
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/nonconformances", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/nonconformances", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_duplicate_idempotency_key_different_payload_conflicts(client, seeded, db):
    owner = await _setup(db, seeded, "11")
    token = await login(client, "admin.ncr11")
    key = idem()
    body1 = _create_body(seeded["site_id"], owner.id, ncr_number="NCR-IDEM-A")
    body1["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/nonconformances", json=body1, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    body2 = _create_body(seeded["site_id"], owner.id, ncr_number="NCR-IDEM-B")
    body2["idempotency_key"] = key
    resp2 = await client.post("/qms/v1/nonconformances", json=body2, headers=auth_headers(token))
    assert resp2.status_code == 409, resp2.text
    assert resp2.json()["code"] == "IDEMPOTENCY_CONFLICT"


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.ncr12")
    token = await login(client, "admin.ncr12")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/signature-challenges", json={"action": "disposition"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_signature_challenge_404_for_missing_ncr(client, seeded, db):
    owner = await _setup(db, seeded, "13")
    token = await login(client, "admin.ncr13")
    resp = await client.post(
        f"/qms/v1/nonconformances/{uuid.uuid4()}/signature-challenges", json={"action": "disposition"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_signature_challenge_round_trip_signs_disposition(client, seeded, db):
    owner = await _setup(db, seeded, "14", signed=True)
    await _indep_qa_releaser(db, seeded, "qa.ncr14")
    token = await login(client, "admin.ncr14")
    signer_token = await login(client, "qa.ncr14")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/signature-challenges", json={"action": "disposition"},
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Released"  # Document 106 section 9 row 84

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "RETURN", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "return to supplier per receiving inspection failure",
            "challenge_id": body["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


# --- Reopen (SG-069 resolved 2026-10-09, mirrors qms_deviation/capa reopen) ----------------------


async def _close_via_return(client, token, ncr_id, next_version):
    """Drives an NCR to CLOSED via the RETURN disposition path, returning the version after close."""
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "RETURN", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "return to supplier per receiving inspection failure",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "confirmation": {"note": "confirmed returned to supplier"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/close",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "conclusion": "Returned to supplier; no further action."},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return next_version + 1


async def test_reopen_rejected_from_non_closed_state(client, seeded, db):
    owner = await _setup(db, seeded, "30", signed=False)
    token = await login(client, "admin.ncr30")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/reopen",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": 3, "reason": "new evidence", "new_evidence": "retest shows OOS"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_reopen_requires_reason_and_new_evidence(client, seeded, db):
    owner = await _setup(db, seeded, "31", signed=False)
    token = await login(client, "admin.ncr31")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)
    next_version = await _close_via_return(client, token, ncr_id, next_version)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/reopen",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "reason": "  ", "new_evidence": ""},
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_reopen_then_reclose_cycle(client, seeded, db):
    owner = await _setup(db, seeded, "32", signed=False)
    token = await login(client, "admin.ncr32")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)
    next_version = await _close_via_return(client, token, ncr_id, next_version)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/reopen",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "reason": "Supplier disputes the disposition with new COA evidence.",
            "new_evidence": "Supplier-submitted retest COA shows result within spec.",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is None  # unsigned, same as deviation/CAPA reopen
    next_version += 1

    # ncr.view isn't granted to any role in this test fixture (a pre-existing gap, unrelated to reopen) --
    # read the row directly rather than through GET /qms/v1/nonconformances/{id}.
    record = await db.get(NonconformanceRecord, uuid.UUID(ncr_id))
    assert record.state == "REOPENED"
    assert len(record.reopen_history) == 1
    assert record.reopen_history[0]["new_evidence"] == "Supplier-submitted retest COA shows result within spec."
    assert record.closed_at is not None  # prior closure preserved, not cleared

    # Reopened NCR can go straight back to CLOSED (matching Document 26's own REOPENED breadth).
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/close",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "conclusion": "Re-reviewed with supplier COA; original disposition stands."},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_reopen_then_reevaluate_cycle(client, seeded, db):
    owner = await _setup(db, seeded, "33", signed=False)
    token = await login(client, "admin.ncr33")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)
    next_version = await _close_via_return(client, token, ncr_id, next_version)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/reopen",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "reason": "New lab result changes the disposition basis.", "new_evidence": "Second retest confirms OOS, not a lab error.",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    # Re-entering EVALUATION from REOPENED works the same as entering it from SEGREGATED.
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/evaluate",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "evaluation": {"usability": "not usable", "quality_impact": "major", "safety_impact": "none",
                           "performance_impact": "none", "investigation_needed": False},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["aggregate_id"] == ncr_id


# --- Re-verification (project-owner-directed 2026-10-09): VERIFICATION now self-loops, and every ------
# --- verify() call is preserved in verification_history rather than overwriting the prior round. ------


async def test_reverify_appends_history_without_losing_prior_round(client, seeded, db):
    owner = await _setup(db, seeded, "34", signed=False)
    token = await login(client, "admin.ncr34")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "SCRAP", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "scrap per QA disposition",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    # First verification round.
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "confirmation": {"note": "first pass -- destruction certificate pending"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    # Re-verification -- previously unreachable (VERIFICATION had no self-loop).
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "confirmation": {"note": "second pass -- destruction certificate DC-001 now on file"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    record = await db.get(NonconformanceRecord, uuid.UUID(ncr_id))
    assert record.state == "VERIFICATION"
    assert len(record.verification_history) == 2
    assert record.verification_history[0]["confirmation"]["note"] == "first pass -- destruction certificate pending"
    assert record.verification_history[1]["confirmation"]["note"] == "second pass -- destruction certificate DC-001 now on file"
    # The single `verification` field still reflects only the latest round (existing consumers unchanged).
    assert record.verification["confirmation"]["note"] == "second pass -- destruction certificate DC-001 now on file"

    # Still closeable afterwards.
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/close",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "conclusion": "Destruction certificate confirmed on second verification pass."},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def test_reverify_preserves_disposition_evidence_type(client, seeded, db):
    """A re-verify on a REWORK/REPAIR disposition still requires reinspection_evidence, not confirmation
    -- the evidence type is inherited from the original disposition, not from the re-verify call."""
    owner = await _setup(db, seeded, "35", signed=False)
    token = await login(client, "admin.ncr35")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "REWORK", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "rework per QA disposition", "rework_route": {"route": "reprocess step 4"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "reinspection_evidence": {"result": "pass, first retest"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    # Re-verify with confirmation instead of reinspection_evidence must be rejected -- REWORK's evidence
    # type is reinspection_evidence, inherited from the original disposition.
    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "confirmation": {"note": "wrong evidence type"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "REINSPECTION_REQUIRED"

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "reinspection_evidence": {"result": "pass, second retest"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


# --- GET detail resolves actor ids to names (project-owner-directed 2026-10-09) ------------------


async def test_get_detail_resolves_actor_names_not_raw_uuids(client, seeded, db):
    owner = await _setup(db, seeded, "36", signed=False)
    token = await login(client, "admin.ncr36")
    ncr_id = await _create(client, token, seeded["site_id"], owner.id)
    next_version = await _segregate_and_evaluate(client, token, ncr_id)

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/disposition",
        json={
            "idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version,
            "disposition_type": "USE_AS_IS", "affected_scope": [{"record_type": "material_lot", "record_id": str(uuid.uuid4())}],
            "justification": "use as is per QA disposition", "use_as_is_authorized_by": str(owner.id),
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/verify",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "confirmation": {"note": "use-as-is confirmed"}},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/close",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "conclusion": "closing for name-resolution test"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    next_version += 1

    resp = await client.post(
        f"/qms/v1/nonconformances/{ncr_id}/reopen",
        json={"idempotency_key": idem(), "ncr_id": ncr_id, "expected_version": next_version, "reason": "name-resolution re-check", "new_evidence": "new evidence text"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/qms/v1/nonconformances/{ncr_id}", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    detail = resp.json()

    assert detail["owner_username"] == f"admin.ncr36"
    assert detail["owner_full_name"] == "Test Admin"

    use_as_is = next(d for d in detail["dispositions"] if d["disposition_type"] == "USE_AS_IS")
    assert use_as_is["use_as_is_authorized_by_username"] == "admin.ncr36"
    assert use_as_is["use_as_is_authorized_by_full_name"] == "Test Admin"

    assert detail["verification"]["verified_by_username"] == "admin.ncr36"
    assert detail["verification_history"][0]["verified_by_username"] == "admin.ncr36"
    assert detail["closure_history"][0]["closed_by_username"] == "admin.ncr36"
    assert detail["reopen_history"][0]["reopened_by_username"] == "admin.ncr36"

    # Raw ids are preserved unchanged alongside the resolved names -- nothing is replaced, only enriched.
    assert detail["owner_subject_id"] == str(owner.id)
    assert detail["closure_history"][0]["closed_by"] == str(owner.id)
