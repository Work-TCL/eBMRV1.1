"""Document 34 (SPEC-QMS-009) -- the buildable slice: create internal audit -> start -> findings ->
response -> verify (signed) -> close (signed), matching the module's own 6-op API list and the fold-in
pattern documented in app/modules/qms/internal_audit_models.py's module docstring. New module.
AUDIT-FR-008/012/015/016/017 are out of scope this pass -- see docs/generated/18_SPEC_GAPS.md SG-101; the
broader "own function" half of AUDIT-FR-003 is out of scope -- see SG-102.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.iam.models import User, UserSiteRole
from app.modules.qms.internal_audit_models import AuditFinding, InternalAudit
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


async def _setup(db, seeded, tag, *, signed=False, close_signed=None, verify_signed=None):
    close_signed = signed if close_signed is None else close_signed
    verify_signed = signed if verify_signed is None else verify_signed
    async with db.begin():
        owner = await _make_admin(db, seeded, f"admin.audit{tag}")
        db.add(SignaturePolicy(record_type="internal_audit", action="start", meaning="Performed", signature_required=signed))
        db.add(SignaturePolicy(record_type="internal_audit", action="close", meaning="Approved", signature_required=close_signed))
        db.add(SignaturePolicy(record_type="audit_finding", action="verify", meaning="Verified", signature_required=verify_signed))
    return owner


def _create_body(site_id, lead_auditor_id, **overrides):
    body = {
        "idempotency_key": idem(), "site_id": str(site_id), "audit_number": f"IA-{uuid.uuid4().hex[:8]}",
        "program_ref": "2026 Annual Audit Program", "criteria_refs": {"standards": ["21 CFR 211", "ISO 13485"]},
        "lead_auditor_id": str(lead_auditor_id), "scheduled_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "site_scope": {"site": "SITE1"}, "process_scope": {"process": "Warehouse"},
    }
    body.update(overrides)
    return body


async def _create_audit(client, token, site_id, lead_auditor_id, **overrides):
    resp = await client.post("/qms/v1/audits", json=_create_body(site_id, lead_auditor_id, **overrides), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _start_audit(client, token, audit_id, expected_version=1, **overrides):
    body = {"idempotency_key": idem(), "audit_id": audit_id, "expected_version": expected_version}
    body.update(overrides)
    resp = await client.post(f"/qms/v1/audits/{audit_id}/start", json=body, headers=auth_headers(token))
    return resp


async def _add_finding(client, token, audit_id, audit_expected_version, owner_id, **overrides):
    body = {
        "idempotency_key": idem(), "audit_id": audit_id, "audit_expected_version": audit_expected_version,
        "finding_number": f"FIND-{uuid.uuid4().hex[:8]}", "requirement_ref": "21 CFR 211.42(c)",
        "observation": "Warehouse temperature log had a 6-hour gap with no documented cause.",
        "severity": "major", "owner_subject_id": str(owner_id),
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/audits/{audit_id}/findings", json=body, headers=auth_headers(token))
    return resp


async def _respond(client, token, finding_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "finding_id": finding_id, "expected_version": expected_version,
        "correction": "Temperature log gap investigated and closed.", "root_cause": "Logger battery failure.",
        "action": "Replace battery and add battery-health alarm.",
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/findings/{finding_id}/response", json=body, headers=auth_headers(token))
    return resp


async def _verify(client, token, finding_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "finding_id": finding_id, "expected_version": expected_version,
        "verification_notes": "Battery replaced and alarm confirmed functional on walkthrough.", "effective": True,
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/findings/{finding_id}/verify", json=body, headers=auth_headers(token))
    return resp


async def _close(client, token, audit_id, expected_version, **overrides):
    body = {
        "idempotency_key": idem(), "audit_id": audit_id, "expected_version": expected_version,
        "conclusion": "All findings verified effective; audit closed.",
    }
    body.update(overrides)
    resp = await client.post(f"/qms/v1/audits/{audit_id}/close", json=body, headers=auth_headers(token))
    return resp


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/qms/v1/audits", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_audit_requires_scope(client, seeded, db):
    owner = await _setup(db, seeded, "1")
    token = await login(client, "admin.audit1")
    resp = await client.post(
        "/qms/v1/audits", json=_create_body(seeded["site_id"], owner.id, site_scope=None, process_scope=None), headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "AUDIT_SCOPE_INCOMPLETE"


async def test_create_audit_rejects_auditor_auditing_self(client, seeded, db):
    owner = await _setup(db, seeded, "2")
    token = await login(client, "admin.audit2")
    resp = await client.post(
        "/qms/v1/audits", json=_create_body(seeded["site_id"], owner.id, auditees=[str(owner.id)]), headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "AUDITOR_SOD_CONFLICT"


async def test_full_lifecycle_success(client, seeded, db):
    owner = await _setup(db, seeded, "3", signed=False)
    token = await login(client, "admin.audit3")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)

    resp = await _start_audit(client, token, audit_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2

    resp = await _add_finding(client, token, audit_id, 2, owner.id, evidence={"interview": "Warehouse operator, 2026-08-25"})
    assert resp.status_code == 200, resp.text  # finding created; audit 2 -> 3 (FINDINGS_OPEN, first finding)
    finding_id = resp.json()["aggregate_id"]

    audit = await db.get(InternalAudit, uuid.UUID(audit_id))
    assert audit.state == "FINDINGS_OPEN"
    assert audit.version == 3

    resp = await _respond(client, token, finding_id, 1, capa_required=True, capa_rationale="Systemic monitoring gap.")
    assert resp.status_code == 200, resp.text  # finding 1 -> 2

    resp = await _verify(client, token, finding_id, 2)
    assert resp.status_code == 200, resp.text  # finding 2 -> 3

    finding = await db.get(AuditFinding, uuid.UUID(finding_id))
    assert finding.state == "VERIFIED"
    assert finding.verification["effective"] is True
    assert finding.evidence == {"interview": "Warehouse operator, 2026-08-25"}
    assert finding.capa_required is True
    assert finding.capa_rationale == "Systemic monitoring gap."

    resp = await _close(client, token, audit_id, 3)
    assert resp.status_code == 200, resp.text  # audit 3 -> 4
    assert resp.json()["resulting_version"] == 4

    await db.refresh(audit)  # the app committed via a different session; the identity-mapped object is stale
    assert audit.state == "CLOSED"
    assert audit.actual_end_at is not None

    # TC-034-M11 equivalent: exactly one audit_events row for the create command.
    create_rows = (
        await db.execute(
            select(AuditEvent).where(AuditEvent.aggregate_type == "internal_audit", AuditEvent.aggregate_id == audit.id, AuditEvent.action == "Created")
        )
    ).scalars().all()
    assert len(create_rows) == 1


async def test_close_blocked_before_report_approved(client, seeded, db):
    owner = await _setup(db, seeded, "4", signed=False)
    token = await login(client, "admin.audit4")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    resp = await _start_audit(client, token, audit_id, 1)
    assert resp.status_code == 200, resp.text

    resp = await _close(client, token, audit_id, 2)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "AUDIT_CLOSURE_BLOCKED"


async def test_close_requires_all_findings_verified(client, seeded, db):
    owner = await _setup(db, seeded, "5", signed=False)
    token = await login(client, "admin.audit5")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    await _start_audit(client, token, audit_id, 1)
    resp = await _add_finding(client, token, audit_id, 2, owner.id)
    finding_id = resp.json()["aggregate_id"]
    await _respond(client, token, finding_id, 1)

    resp = await _close(client, token, audit_id, 3)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "FINDING_VERIFICATION_REQUIRED"


async def test_verify_requires_response_first(client, seeded, db):
    owner = await _setup(db, seeded, "6", signed=False)
    token = await login(client, "admin.audit6")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    await _start_audit(client, token, audit_id, 1)
    resp = await _add_finding(client, token, audit_id, 2, owner.id)
    finding_id = resp.json()["aggregate_id"]

    resp = await _verify(client, token, finding_id, 1)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "FINDING_RESPONSE_REQUIRED"


async def test_repeat_finding_detected_across_audits(client, seeded, db):
    owner = await _setup(db, seeded, "7", signed=False)
    token = await login(client, "admin.audit7")

    first_audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    await _start_audit(client, token, first_audit_id, 1)
    resp = await _add_finding(client, token, first_audit_id, 2, owner.id, requirement_ref="21 CFR 211.100(a)")
    first_finding_id = resp.json()["aggregate_id"]

    second_audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    await _start_audit(client, token, second_audit_id, 1)
    resp = await _add_finding(client, token, second_audit_id, 2, owner.id, requirement_ref="21 CFR 211.100(a)")
    assert resp.status_code == 200, resp.text
    second_finding_id = resp.json()["aggregate_id"]

    first_finding = await db.get(AuditFinding, uuid.UUID(first_finding_id))
    second_finding = await db.get(AuditFinding, uuid.UUID(second_finding_id))
    assert first_finding.is_repeat_finding is False
    assert second_finding.is_repeat_finding is True


async def test_stale_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "8", signed=False)
    token = await login(client, "admin.audit8")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)

    resp = await _start_audit(client, token, audit_id, 99)
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_idempotent_replay_returns_same_receipt(client, seeded, db):
    owner = await _setup(db, seeded, "9", signed=False)
    token = await login(client, "admin.audit9")
    key = idem()
    body = _create_body(seeded["site_id"], owner.id)
    body["idempotency_key"] = key
    resp1 = await client.post("/qms/v1/audits", json=body, headers=auth_headers(token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/qms/v1/audits", json=body, headers=auth_headers(token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]

    body2 = dict(body)
    body2["program_ref"] = "Different Program"
    resp3 = await client.post("/qms/v1/audits", json=body2, headers=auth_headers(token))
    assert resp3.status_code == 409, resp3.text
    assert resp3.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_start_requires_signature_when_policy_requires_it(client, seeded, db):
    owner = await _setup(db, seeded, "10", signed=True)
    token = await login(client, "admin.audit10")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    resp = await _start_audit(client, token, audit_id, 1)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_close_requires_signature_when_policy_requires_it(client, seeded, db):
    # start/verify unsigned, close signed -- isolates close()'s own Document 106 row 98 requirement.
    owner = await _setup(db, seeded, "13", signed=False, close_signed=True)
    token = await login(client, "admin.audit13")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    await _start_audit(client, token, audit_id, 1)
    resp = await _add_finding(client, token, audit_id, 2, owner.id)
    finding_id = resp.json()["aggregate_id"]
    await _respond(client, token, finding_id, 1)
    await _verify(client, token, finding_id, 2)

    resp = await _close(client, token, audit_id, 3)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_verify_requires_signature_when_policy_requires_it(client, seeded, db):
    # start/close unsigned, verify signed -- isolates verify()'s own Document 106 row 100 requirement.
    owner = await _setup(db, seeded, "14", signed=False, verify_signed=True)
    token = await login(client, "admin.audit14")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    await _start_audit(client, token, audit_id, 1)
    resp = await _add_finding(client, token, audit_id, 2, owner.id)
    finding_id = resp.json()["aggregate_id"]
    await _respond(client, token, finding_id, 1)

    resp = await _verify(client, token, finding_id, 2)
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_actor_without_permission_is_denied(client, seeded, db):
    owner = await _setup(db, seeded, "11", signed=False)
    token = await login(client, "operator1")  # Operator role has no internal_audit.* grant (seeded fixture)
    resp = await client.post(
        "/qms/v1/audits", json=_create_body(seeded["site_id"], owner.id), headers=auth_headers(token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_missing_expected_version_rejected(client, seeded, db):
    owner = await _setup(db, seeded, "12", signed=False)
    token = await login(client, "admin.audit12")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)

    body = {"idempotency_key": idem(), "audit_id": audit_id}
    resp = await client.post(f"/qms/v1/audits/{audit_id}/start", json=body, headers=auth_headers(token))
    assert resp.status_code == 422, resp.text  # FastAPI/Pydantic request validation: expected_version required


# --- Signature-challenge ceremony entry point (SG-138 engineering half) -------------------------


async def test_audit_signature_challenge_fails_closed_when_policy_unresolved(client, seeded, db):
    async with db.begin():
        owner = await _make_admin(db, seeded, "admin.audit20")
    token = await login(client, "admin.audit20")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    resp = await client.post(
        f"/qms/v1/audits/{audit_id}/signature-challenges", json={"action": "start"}, headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_audit_signature_challenge_404_for_missing_audit(client, seeded, db):
    owner = await _setup(db, seeded, "21")
    token = await login(client, "admin.audit21")
    resp = await client.post(
        f"/qms/v1/audits/{uuid.uuid4()}/signature-challenges", json={"action": "start"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_audit_signature_challenge_round_trip_signs_start(client, seeded, db):
    owner = await _setup(db, seeded, "22", signed=True)
    token = await login(client, "admin.audit22")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)

    resp = await client.post(
        f"/qms/v1/audits/{audit_id}/signature-challenges", json={"action": "start"}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Performed"

    resp = await _start_audit(
        client, token, audit_id, 1, challenge_id=body["challenge_id"], reauth_password=DEMO_PASSWORD,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


async def test_finding_signature_challenge_404_for_missing_finding(client, seeded, db):
    owner = await _setup(db, seeded, "23")
    token = await login(client, "admin.audit23")
    resp = await client.post(
        f"/qms/v1/findings/{uuid.uuid4()}/signature-challenges", json={"action": "verify"}, headers=auth_headers(token),
    )
    assert resp.status_code == 404, resp.text


async def test_finding_signature_challenge_round_trip_signs_verify(client, seeded, db):
    # start/close unsigned so _start_audit() below can succeed without a challenge; verify_signed=True
    # is the actual behaviour under test.
    owner = await _setup(db, seeded, "24", signed=False, verify_signed=True)
    token = await login(client, "admin.audit24")
    audit_id = await _create_audit(client, token, seeded["site_id"], owner.id)
    resp = await _start_audit(client, token, audit_id, 1)
    assert resp.status_code == 200, resp.text  # 1 -> 2
    resp = await _add_finding(client, token, audit_id, 2, owner.id)
    assert resp.status_code == 200, resp.text
    finding_id = resp.json()["aggregate_id"]
    resp = await _respond(client, token, finding_id, 1)
    assert resp.status_code == 200, resp.text  # finding 1 -> 2

    resp = await client.post(
        f"/qms/v1/findings/{finding_id}/signature-challenges", json={"action": "verify"}, headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["meaning"] == "Verified"

    resp = await _verify(
        client, token, finding_id, 2, challenge_id=body["challenge_id"], reauth_password=DEMO_PASSWORD,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None
